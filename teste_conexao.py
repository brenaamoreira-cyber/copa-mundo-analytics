from google.cloud import bigquery
import os
from dotenv import load_dotenv

load_dotenv()

client=bigquery.Client(project=os.getenv("world-cup-analytics"))

datasets=list(client.list_datasets())
print ("Conexão OK!")
print([d.dataset_id for d in datasets])