"""
Ingest to elasticsearch
"""
import logging
logging.basicConfig(format='%(levelname)s :: %(asctime)s :: %(message)s', level=logging.WARNING)
from elasticsearch_dsl import Document, Text, connections, Integer, Float
import pymongo
from pymongo import MongoClient
import os
import click
from schema import Pdf, Page, PageObject, ObjectContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, defer
from sqlalchemy.sql.expression import func
import json
engine = create_engine(f'mysql://{os.environ["MYSQL_USER"]}:{os.environ["MYSQL_PASSWORD"]}@{os.environ["MYSQL_HOST"]}:{os.environ["MYSQL_PORT"]}/cosmos', pool_pre_ping=True)
Session = sessionmaker()
Session.configure(bind=engine)

class Object(Document):
    # Not clear if we want to search the context of the header, the context of the object, or both

    cls = Text()
    dataset_id = Text()
    context_id = Integer()
    content = Text()
    area = Integer()
#    init_cls_confidences = Float()
    postprocessing_confidence = Float()
    pp_rule_cls = Text()
    annotated_cls = Text()
    pdf_name = Text()

    class Index:
        name = 'object'
        settings = {
                'number_of_shards': 1,
                'number_of_replicas': 0
        }

class Context(Document):
    # Not clear if we want to search the context of the header, the context of the object, or both
    cls = Text()
    header_id = Integer() # same as _id
    dataset_id = Text()
    content = Text()
    header_content = Text()
    pdf_name = Text()

    # Hmm these are really filters at the _object_ level, not the _context_ level...
#    area = Integer()
#    base_confidence = Float()
#    postprocessing_confidence = Float()

    class Index:
        name = 'context'
        settings = {
                'number_of_shards': 1,
                'number_of_replicas': 0
        }


def ingest_elasticsearch(objects, code, sections, tableContexts, figureContexts, equationContexts):
    """
    Ingest some mongo collections to elasticsearch
    """
    connections.create_connection(hosts=['es01'])
    Context.init()
    session = Session()
#    logging.info("Querying for contexts")
#    contexts = session.execute('SELECT oc.*, p.dataset_id FROM object_contexts oc JOIN (SELECT dataset_id, id FROM pdfs) p ON oc.pdf_id = p.id')
#    logging.info("Writing to ES")
#    for c in contexts:
#        logging.info(f"Found a {c['cls']}")
#        Context(_id = str(c['id']),
#                header_id = c['header_id'],
#                cls = c['cls'],
#                dataset_id = c['dataset_id'],
#                header_content = c['header_content'],
#                content = c['content']
#                ).save()
#
#    Context._index.refresh()
    Object.init()

    conn = engine.connect()
    logging.info("Getting objects")
    objects = conn.execute('SELECT po.id, po.page_id, po.context_id, po.bounding_box, po.cls, po.content, po.init_cls_confidences, po.confidence, po.pp_rule_cls, po.annotated_cls, pdfs.dataset_id, pdfs.pdf_name FROM page_objects po, pdfs, pages WHERE pdfs.id = pages.pdf_id AND pages.id = po.page_id')
    logging.info("Here we go!")
    for po in objects:
        obj = {column:value for column, value in po.items()}
        bb = json.loads(obj['bounding_box'])
        tlx, tly, brx, bry = bb
        area = (brx - tlx) * (bry - tly)
        Object(_id = str(obj['id']),
                cls = obj['cls'],
                dataset_id = obj['dataset_id'],
                context_id = obj['context_id'],
                content = obj['content'],
                area = area,
                base_confidence = json.loads(obj['init_cls_confidences'])[0][0],
                postprocessing_confidence = obj['confidence'],
                pp_rule_cls = obj['pp_rule_cls'],
                annotated_cls = obj['annotated_cls'],
                pdf_name = obj['pdf_name']
                ).save()



def load_pages(coll, buffer_size):
    """
    Load pages from a given collection
    """
    current_docs = []
    for doc in coll.find().batch_size(buffer_size):
        current_docs.append(doc)
        if len(current_docs) == buffer_size:
            yield current_docs
            current_docs = []
    yield current_docs

@click.command()
@click.option('--objects/--no-objects')
@click.option('--code/--no-code')
@click.option('--sections/--no-sections')
@click.option('--tables/--no-tables')
@click.option('--figures/--no-figures')
@click.option('--equations/--no-equations')
def ingest(objects, code, sections, tables, figures, equations):
    logging.info('Starting ingestion to elasticsearch')
    ingest_elasticsearch(objects, code, sections, tables, figures, equations)
    logging.info('Ending ingestion to elasticsearch')


if __name__ == '__main__':
    ingest()
