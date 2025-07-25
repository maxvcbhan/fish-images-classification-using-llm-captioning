import pandas as pd
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
from elasticsearch.helpers import bulk
import os

class ElasticsearchManager:
    def __init__(self, es_endpoint, es_username, es_password):
        self.es = Elasticsearch(
        [es_endpoint],
        http_auth=(es_username, es_password),
        verify_certs=False
    )
        
        self.mappings = {
                        "properties": {
                            "fish_name": {
                                "type": "text"
                            },
                            "general_description": {
                                "type": "semantic_text"
                            },
                            "image_links": {
                                "type": "text"
                            },
                            "embedding": {
                                "type": "dense_vector",
                                "dims": 1024,  # Adjust the dimension based on your model's output
                                "similarity": "cosine"
                            }
                        }
                    }

    def create_index(self, index_name):
        if not self.es.indices.exists(index=index_name):
            print(f"Creating index '{index_name}'...")

            mappings = {
                "mappings": {
                    "properties": {
                        "fish_name": {
                            "type": "text"
                        },
                        "general_description": {
                            "type": "text"  # 'semantic_text' is not valid; use 'text'
                        },
                        "image_links": {
                            "type": "text"
                        },
                        "embedding": {
                            "type": "dense_vector",
                            "dims": 1024,  # Adjust the dimension based on your model's output
                            "similarity": "cosine",
                            "index": True  # Set to True + additional settings for ANN search
                        }
                    }
                }
            }

            response = self.es.indices.create(index=index_name, body=mappings)
            print(response)
            print(f"Index '{index_name}' created.")
        else:
            print(f"Index '{index_name}' already exists.")
        return index_name

    def delete_index(self, index_name):
        try:
            response = self.es.indices.delete(index=index_name)
            print(f"✓ Index '{index_name}' deleted successfully")
            return response
        except Exception as e:
            print(f"✗ Error deleting index: {e}")
    
    def list_all_index(self, creator="user"):
        """
        Args:
            creator (str):
                - "user": indices not starting with '.'
                - "system": indices starting with '.'
                - "all": all indices categorized
        """
        try:
            # Fixed: Use keyword argument
            user_index = []
            system_index = []
            indices = self.es.indices.get_alias()
            for index_name in indices.keys():
                count = self.get_document_count(index_name, silent=True)
                if not(index_name.startswith('.')):
                    # print(f"  - {index_name} ({count} documents)")
                    user_index.append(index_name)
                else:
                    system_index.append(index_name)
            print(f"User Indices: {user_index}")
            if creator == "user":
                return user_index
            elif creator == "system":
                return system_index
            elif creator == "all":
                return indices.keys()
        except Exception as e:
            print(f"✗ Error listing indices: {e}")
    
    def get_document_count(self, index_name, silent=False):
        try:
            response = self.es.count(index=index_name)
            count = response['count']
            if not silent:
                print(f"📊 Index '{index_name}' contains {count} documents")
            return count
        except Exception as e:
            if not silent:
                print(f"✗ Error getting document count: {e}")
            return 0

    def ingest_df_to_elasticsearch(self, df, index_name):
        print('creating index...')
        self.create_index(index_name)
        print("Ingesting DataFrame to Elasticsearch...")
        # Prepare bulk actions
        actions = [
            {
                "_index": index_name,
                "_source": {
                    "fish_name": row["Fish Name"],
                    "general_description": row["Summary Description"],
                    "image_links": row["Image Links"],
                    "embedding": row["embedding"]
                }
            }
            for _, row in df.iterrows()
        ]
        print("finish actions...")  # Debugging line to check actions

        # Upload to Elasticsearch

        # print(actions)
        success, errors = bulk(self.es, actions)
        print(f"Success: {success}, Errors: {errors}")

    def get_index_info(self, index_name):
        try:
            if not self.es.indices.exists(index=index_name):
                print(f"❌ Index '{index_name}' not found")
                return None
            
            # Get mapping and count
            mapping = self.es.indices.get_mapping(index=index_name)[index_name]['mappings']
            count = self.es.count(index=index_name)['count']
            
            # Get sample document
            sample = self.es.search(index=index_name, body={"size": 1})
            sample_doc = sample['hits']['hits'][0]['_source'] if sample['hits']['hits'] else {}
            
            print(f"📊 {index_name}: {count} rows")
            print("Columns:")
            for field, value in sample_doc.items():
                field_type = type(value).__name__
                print(f"  {field}: {field_type}")
            
            return {'rows': count, 'columns': list(sample_doc.keys()), 'sample': sample_doc}
            
        except Exception as e:
            print(f"✗ Info error: {e}")

