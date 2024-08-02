from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from redis import Redis
from ninja import NinjaAPI
from .model import News
from .db import NewsModel, Session
from sqlalchemy.orm import sessionmaker
import asyncio
import nats
from nats.errors import TimeoutError
import os
import csv
import shutil
from pytube import YouTube
import xml.etree.ElementTree as ElementTree
from html import unescape
from . import video_pb2 as Video
from datetime import datetime
from config import celery_app
from celery.result import AsyncResult
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI, ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma


redis = Redis.from_url(settings.REDIS_URL)


db = NinjaAPI()

@db.get("/")
def view(request):
    return JsonResponse({"message": "Welcome to Ninja News"})

@db.get("/get-all-records")
def get_all_records(request):

    session = Session()

    query = session.query(NewsModel.title, NewsModel.channel, NewsModel.category, NewsModel.publication_date, NewsModel.url, NewsModel.transcript, NewsModel.id).order_by(NewsModel.publication_date.desc())
    all_records = query.all() 
    session.close()

    columns = ["Title", "Channel", "Category", "Publication Date", "URL", "Transcript", "Summary"]

    rows = []
    for record in all_records:
        row = {}
        for i, value in enumerate(record):
            row[columns[i]] = value
        rows.append(row)

    data = {
        "columns": columns,
        "rows": rows
    }

    return JsonResponse(data)
    
def xml_to_srt(xml_captions):
    segments = []
    root = ElementTree.fromstring(xml_captions)
    for child in root.iter("p"):
        text = child.text or ""
        if child.text is None:
            for sub_child in child:
                if sub_child.text is not None:
                    text += sub_child.text
        caption = unescape(text.replace("\n", " ").replace("  ", " "),)
        try:
            duration = float(child.attrib["d"]) / 1000.0
        except KeyError:
            duration = 0.0
        try:
            start = float(child.attrib["t"]) / 1000.0
        except KeyError:
            start = 0.0
        end = start + duration
        line = "{text}\n".format(
            text=caption,
        )
        segments.append(line)
    return "\n".join(segments).strip()

async def download_vids(num, offset):

    nc = await nats.connect("jetstream")
    js = nc.jetstream()
    await js.add_stream(name="news-videos", subjects=["news-videos"])
    videos_path = os.path.join(settings.BASE_DIR, "news/videos.csv")
    video_file = open(videos_path, "r")

    videos = []
    n = 0
    csv_reader = csv.reader(video_file)
    for line in csv_reader:
        if offset > 0:
            offset -= 1
            continue

        if num > 0:
            num -= 1
        else:
            break
        
        url = line[0]

        category = line[1]
        yt = YouTube(url)
        yt.bypass_age_gate()
        transcript = yt.captions
        if 'a.en' in transcript.keys():
            transcript = transcript['a.en'].xml_captions
            transcript = xml_to_srt(transcript)
        elif 'en' in transcript.keys():
            transcript = transcript['en'].xml_captions
            transcript = xml_to_srt(transcript)

        if transcript == "":
            transcript = "No transcript available"

        if type(transcript) != str:
            transcript = "No transcript available"

        channel = yt.author
        publication_date = yt.publish_date.strftime("%Y-%m-%d")

        video = Video.Video()
        video.title = yt.title
        video.url = url
        video.transcript = transcript
        video.channel = channel
        video.publication_date = publication_date
        video.category =  category

        ack = await js.publish("news-videos", video.SerializeToString())
        n+=1
        

    await nc.close()
    return n

@celery_app.task(name="push_to_js")
def download_videos_to_js(num, offset):
    print("Downloading videos")
    n = asyncio.run(download_vids(num, offset))
    return n

async def consume_vids():
    nc = await nats.connect("jetstream")
    js = nc.jetstream()
    psub = await js.pull_subscribe("news-videos", "psub")
    session = Session()

    video = Video.Video()

    n = 0
    try: 
        for i in range(0, 100):
            msgs = await psub.fetch(1)
            data_batch = []
            for msg in msgs:
                await msg.ack()
                video.ParseFromString(msg.data)
                n+=1

                new_news_record = News(
                    title = video.title,
                    url = video.url,
                    transcript = video.transcript,
                    channel = video.channel,
                    publication_date = video.publication_date,
                    category = video.category
                )

                db_record = NewsModel(**new_news_record.dict())
                exists = session.query(NewsModel).filter_by(url=db_record.url).first()

                if exists is None:
                    session.add(db_record)
                else:
                    exists.transcript = db_record.transcript
                    exists.updated_at = datetime.utcnow()
                    exists.title = db_record.title
        session.commit()
        session.close()
        return n
    except TimeoutError:
        session.commit()
        session.close()
        return n

@celery_app.task(name="insert_into_db")
def insert_videos_into_db():
    print("Inserting videos")
    n = asyncio.run(consume_vids())
    return n

@db.get("/download-videos")
def download_videos(request, n:int, o:int):
    x = download_videos_to_js.apply_async(args=[n, o])
    res = AsyncResult(x.id)
    n = x.get()
    return JsonResponse({"message": "Downloaded videos", "n": n})

@db.get("/insert-videos")
def insert_videos(request):
    x = insert_videos_into_db.delay()
    res = AsyncResult(x.id)
    n = x.get()
    return JsonResponse({"message": "Inserted videos", "n": n})

@db.get("/get-summary")
def get_summary(request, id: str):
    
    session = Session()
    query = session.query(NewsModel).filter_by(id=id)
    record = query.first()

    if record is None:
        return JsonResponse({"message": "Video not found"})

    summaryResponse = record.summary

    if record.summary_updated_at is None or (record.summary_updated_at < record.updated_at):

        template = """Summarize the following video in 500 words or less: \n\n{transcript}"""

        prompt = PromptTemplate.from_template(template)

        llm = OpenAI(openai_api_key=os.environ["OPENAI_API_KEY"])

        llm_chain = LLMChain(prompt=prompt, llm=llm)

        # Process transcript to reduce data sent to OpenAI
        processedTranscript = record.transcript
        processedTranscript = processedTranscript.replace("\n", " ")
        processedTranscript = processedTranscript.replace("\r", " ")
        processedTranscript = processedTranscript.replace("\t", " ")
        processedTranscript = ' '.join(processedTranscript.split())
        processedTranscript = processedTranscript.strip()

        try:
            if(int(os.environ["USE_OPEANAI"]) == 1):
                summaryResponse = llm_chain.run(processedTranscript)
            else:
                summaryResponse = "Summary for: " + record.title

            record.summary = summaryResponse

            record.summary_updated_at = datetime.utcnow()

            session.commit()

            print("Generated new summary")
            
        except Exception as e:
            print(e)
            return JsonResponse({"message": "Failed to generate summary due to OpenAI API error. Please try again later."})

    response = {
        "title": record.title,
        "transcript": record.transcript,
        "summary": summaryResponse
    }

    session.close()

    return JsonResponse(response)    

@db.get("/vectorize-data")
def vectorize(request):

    # Remove old data
    if os.path.isdir("./chroma_db"):
        shutil.rmtree("./chroma_db")

    session = Session()

    query = session.query(NewsModel.id, NewsModel.category, NewsModel.transcript)
    records = query.all()

    docs = []

    # Process and document each item in DB
    for record in records:
        processedTranscript = record.transcript
        processedTranscript = processedTranscript.replace("\n", " ")
        processedTranscript = processedTranscript.replace("\r", " ")
        processedTranscript = processedTranscript.replace("\t", " ")
        processedTranscript = ' '.join(processedTranscript.split())
        processedTranscript = processedTranscript.strip()
        doc = Document(page_content=processedTranscript, metadata={"id": str(record.id), "category": record.category})
        docs.append(doc)

    session.close()

    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True
    )

    all_splits = text_splitter.split_documents(docs)

    print("Number of splits: ", len(all_splits))

    # Store chunks in Chroma
    vectorstore = Chroma.from_documents(documents=all_splits, embedding=OpenAIEmbeddings(), persist_directory="./chroma_db")

    return JsonResponse({"message": "Vectorized data"})

@db.get("/search")
def search(request, query: str):

    print("Use OpenAI: ", os.environ["USE_OPEANAI"])

    # If vectorized data does not exist, vectorize it
    if not os.path.isdir("./chroma_db"):
        vectorize(request)

    vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=OpenAIEmbeddings())

    # Retrieve 4 most similar documents
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 6})

    retrieved_docs = retriever.invoke(query)

    # Combine all retrieved documents into a single context
    context = ""

    for doc in retrieved_docs:
        context += ' '.join(doc.page_content.split())
        context += "\n"

    context = context.strip()

    # Generate a prompt using the query and context
    template = """Question: """ + query + """\n\nContext: {context}\n\nInstructions: Craft your response to the question based on your understanding and interpretation of the provided context. Avoid directly copying sections of the context; instead, use it to inform and support your answer. If you do not know the answer, state that you are unable to provide a response."""

    prompt = PromptTemplate.from_template(template)

    llm = OpenAI(openai_api_key=os.environ["OPENAI_API_KEY"])
    llm_chain = LLMChain(prompt=prompt, llm=llm)

    # Generate a response if flag is set
    if int(os.environ["USE_OPEANAI"]) == 1:
        response = llm_chain.run(context)
    else:
        response = template.format(context=context)

    response = response.strip()

    return JsonResponse({"response": response, "context": context})