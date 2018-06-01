
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
    SEARCH_RESULTS_LIMIT = 1000
    search_results = 0
    def gql(query_additions, start):
        return ujson.loads(client.execute('''{
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
            if stars == upper_limit:
                return None, upper_limit, counter
            upper_limit = stars
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
            return
        #print("AAA", upper_limit, counter)
        if r is None:
            return
        for node in results(r):
            try:
                yield url(node)
                counter += 1
            except:
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
                #print("parsing " + file)
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
    print("fetching " + words)
    now = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    targz = os.path.expanduser("~/coda/fetched/search_" + words.replace(" ", "_") + extension + "__" + now.replace(':','-') + ".tar.gz")
    with open(cache_file, "r") as cache:
        cached = set(url.strip() for url in cache.readlines())
        print("cache with " + str(len(cached)) + " urls")
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


for word in ["tensorflow"]: #"pytorch", "matplotlib", "tensorflow"]:
    fetch(word, filters=" language:Python stars:>4", extension=".py")
    
for word in ["d3"]:
    fetch(word, filters=" language:Javascript stars:>4", extension=".js")

for lang, extension in [("Python", ".py"), ("Javascript", ".js"), ("Java", ".java")]:
    for word in ["algorithm", "test", "simple", "tutorial", "examples"]:
        print()
        fetch(word, filters=" language:" + lang + " stars:>4", extension=extension)

for lang, extension in [("Javascript", ".js")]: #, ("Python", ".py")]: #, ("Java", ".java")]:
    print()
    fetch("", filters=" language:" + lang + " stars:>42", extension=extension)

