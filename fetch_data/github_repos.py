
# coding: utf-8

# In[1]:


from graphqlclient import GraphQLClient
import os
import ujson
import sys
import time


# In[2]:


client = GraphQLClient('https://api.github.com/graphql')


# In[3]:


with open(os.path.expanduser("~/github_token"), 'r') as tokenfile:
    token = tokenfile.readlines()[0].strip()
    client.inject_token(token)


# In[4]:


def github_repos(query):
    SEARCH_RESULTS_LIMIT = 1000
    search_results = 0
    def gql(query_additions, start):
        print("querying...")
        sys.stdout.flush()
        response = ujson.loads(client.execute('''{
          search(query: "''' + query + ' ' + query_additions + '", type: REPOSITORY, first: 100' + start + ''') {
            pageInfo {
              hasNextPage
              endCursor
            }
            repositoryCount
            edges {
              node {
                ... on Repository {
                  nameWithOwner
                  defaultBranchRef {
                    name
                  }
                  stargazers {
                    totalCount
                  }
                }
              }
            }
          }
        }'''))
        #print(response); sys.stdout.flush()
        return response
    def results(result):
        #print(result)
        try:
            return [edge["node"] for edge in result["data"]["search"]["edges"]]
        except Exception as e:
            print(result)
            raise e
    first = gql(" sort:stars", "")
    result_count = first["data"]["search"]["repositoryCount"]
    print(result_count, "results")
    def subsequent(previous, upper_limit, counter):
        if counter >= SEARCH_RESULTS_LIMIT:
            stars = results(previous)[-1]["stargazers"]["totalCount"]
            if stars == upper_limit or stars == 0:
                print("stars = upper_limit =", stars)
                return None, upper_limit, counter
            upper_limit = stars + 1
            counter = 0
            after = ""
        else:
            cursor = previous["data"]["search"]["pageInfo"]["endCursor"]
            after = ', after: "' + cursor + '"'
        query_additions = ' sort:stars stars:<' + str(upper_limit) 
        print("query_addditions == ", query_additions)
        return gql(query_additions, after), upper_limit, counter
    counter = 0
    def url(node):
        return "https://github.com/" + node["nameWithOwner"] + "/tarball/" + node["defaultBranchRef"]["name"]
    for node in results(first):
        try:
            yield url(node)
            counter += 1
        except:
            pass
    r = first
    upper_limit = 4200000
    while True:
        try:
            r, upper_limit, counter = subsequent(r, upper_limit, counter)
        except Exception as e:
            print(r)
            print(upper_limit)
            print(counter)
            print(e)
            if "Please wait a few minutes before you try again" in r:
                print("sleeping for 10 minutes...")
                sys.stdout.flush()
                time.sleep(600)
            return
        #print("AAA", upper_limit, counter)
        if r is None:
            return
        for node in results(r):
            try:
                yield url(node)
                counter += 1
            except Exception as e:
                print(e)
                pass
        #print("BBB", upper_limit, counter)


# In[5]:


import urllib3
import shutil

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

http = urllib3.PoolManager()

def get(url, path):
    with http.request('GET', url, preload_content=False) as resp, open(path, 'wb') as out_file:
        shutil.copyfileobj(resp, out_file)

    resp.release_conn()


# In[27]:


from datetime import datetime
from tempfile import TemporaryDirectory
import glob

def extension_files(members, extension):
    for tarinfo in members:
        if os.path.splitext(tarinfo.name)[1] == extension:
            yield tarinfo

import tarfile

import time

def save(url, extension, gzip):
    count = 0
    with TemporaryDirectory() as temp_dir:
        tarpath = os.path.join(temp_dir, 'tar.tar')
        get(url, tarpath)
        with tarfile.open(tarpath, "r") as tar:
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(tar, path=temp_dir, members=extension_files(tar,extension))
        for file in glob.iglob(temp_dir + "/**/*" + extension, recursive=True):
            try:
                filename = file[len(temp_dir)+1:]
                gzip.add(file, arcname=filename)
                count += 1
            except Exception as e:
                print("Error while adding " + file + " from " + url)
                print(e)
    return count


# In[28]:


cache_file = os.path.expanduser("~/coda/fetched_julia/cache")

print("starting...")
sys.stdout.flush()

def fetch(words, filters=" language:Julia", extension=".jl"):
    print("fetching " + words)
    sys.stdout.flush()
    now = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    targz = os.path.expanduser("~/coda/fetched_julia/search_" + words.replace(" ", "_") + extension + "__" + now.replace(':','-') + ".tar.gz")
    with open(cache_file, "r") as cache:
        cached = set(url.strip() for url in cache.readlines())
        print("cache with " + str(len(cached)) + " urls")
        sys.stdout.flush()
    with open(cache_file, "a") as cache, tarfile.open(targz, "x:gz") as gzip:
        for i, url in enumerate(github_repos(words + " " + filters)):
            #print(i, url, "processing")
            sys.stdout.flush()
            if url not in cached:
                try:
                    #print(i, url, "not in cache")
                    sys.stdout.flush()
                    count = save(url, extension, gzip)
                    cache.write(url + "\n")
                    cache.flush()
                    print(i, count, url)
                    sys.stdout.flush()
                except Exception as e:
                    print("Error while fetching " + url)
                    print(e)


#for word in ["algorithm", "test", "simple", "tutorial", "examples", "julia", ""]:
#    fetch(word)

fetch("")
