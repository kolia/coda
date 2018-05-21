
# coding: utf-8

# In[1]:


from graphqlclient import GraphQLClient
import os
import ujson


# In[2]:


client = GraphQLClient('https://api.github.com/graphql')


# In[3]:


with open(os.path.expanduser("~/github_token"), 'r') as tokenfile:
    token = tokenfile.readlines()[0].strip()
    client.inject_token(token)


# In[4]:


def github_repos(query):
    def gql(start):
        return ujson.loads(client.execute('''{
          search(query: "''' + query + '", type: REPOSITORY, first: 100' + start + ''') {
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
                }
              }
            }
          }
        }'''))
    def results(result):
        return [edge["node"] for edge in result["data"]["search"]["edges"]]
    first = gql("")
    result_count = first["data"]["search"]["repositoryCount"]
    print(result_count, "results")
    def subsequent(previous):
        cursor = previous["data"]["search"]["pageInfo"]["endCursor"]
        return gql(', after: "' + cursor + '"')
    counter = 0
    def url(node):
        return "https://github.com/" + node["nameWithOwner"] + "/tarball/" + node["defaultBranchRef"]["name"]
    for node in results(first):
        yield url(node)
        counter += 1
    r = first
    while r["data"]["search"]["pageInfo"]["hasNextPage"]:
        r = subsequent(r)
        for node in results(r):
            yield url(node)
            counter += 1


# In[5]:


import urllib3
import shutil

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

http = urllib3.PoolManager()

def get(url, path):
    with http.request('GET', url, preload_content=False) as resp, open(path, 'wb') as out_file:
        shutil.copyfileobj(resp, out_file)

    resp.release_conn()


# In[6]:


####  MAKE SURE bblfshd is up
# sudo docker run --privileged --rm -it -p 9432:9432 -v bblfsh_cache:/var/lib/bblfshd --name bblfshd bblfsh/bblfshd
#
####  If you are doing this for the first time, also do:
# sudo docker exec -it bblfshd bblfshctl driver install --all

import bblfsh
import tarfile

bblclient = bblfsh.BblfshClient("0.0.0.0:9432")


# In[27]:


from datetime import datetime
from tempfile import TemporaryDirectory
import glob

def extension_files(members, extension):
    for tarinfo in members:
        if os.path.splitext(tarinfo.name)[1] == extension:
            yield tarinfo

from io import BytesIO

import time

def parse(url, extension, gzip):
    count = 0
    with TemporaryDirectory() as temp_dir:
        tarpath = os.path.join(temp_dir, 'tar.tar')
        get(url, tarpath)
        with tarfile.open(tarpath, "r") as tar:
            tar.extractall(path=temp_dir, members=extension_files(tar, extension))
        for file in glob.iglob(temp_dir + "/**/*" + extension, recursive=True):
            try:
                data = str(bblclient.parse(file).uast).encode('utf-8')
                out  = BytesIO(data)
                filename = file[len(temp_dir)+1:] + ".uast"
                #print("                       " + filename)
                info = tarfile.TarInfo(name=filename)
                info.size = len(data)
                gzip.addfile(tarinfo=info, fileobj=out)
                count += 1
            except Exception as e:
                print("Error while parsing " + file + " from " + url)
                print(e)
    return count


# In[28]:


cache_file = os.path.expanduser("~/coda/fetched/cache")

def fetch(words, filters=" language:Python stars:>4", extension=".py"):
    now = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    targz = os.path.expanduser("~/coda/fetched/" + words.replace(" ", "_") + extension + "__" + now + ".tar.gz")
    with open(cache_file, "r") as cache:
        cached = set(url.strip() for url in cache.readlines())
    with open(cache_file, "a") as cache, tarfile.open(targz, "x:gz") as gzip:
        for i, url in enumerate(github_repos(words + " " + filters)):
            if url not in cached:
                try:
                    count = parse(url, extension, gzip)
                    cache.write(url + "\n")
                    cache.flush()
                    print(i, count, url)
                except Exception as e:
                    print("Error while fetching " + url)
                    print(e)


# In[ ]:


for word in ["pytorch", "matplotlib", "tensorflow"]:
    fetch(word, filters=" language:Python stars:>4", extension=".py")
    
for word in ["d3"]:
    fetch(word, filters=" language:Javascript stars:>4", extension=".js")

