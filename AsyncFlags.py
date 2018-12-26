
# coding: utf-8

# In[1]:


import sys
import os
import time

import aiohttp
import aiohttp.web
import asyncio


# In[2]:


async def test():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://httpbin.org/get') as resp:
            print(resp.status)
            print(await resp.text())
try:
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test())
    
finally:
    loop.close()


# In[3]:


CONT10 = 'RU US IN BD NG PK MX PH VN CN'.split()
URL = 'http://flupy.org/data/flags'
DEST_DIR = r'C:\Users\Public\Downloads'
params = CONT10, URL, DEST_DIR


# In[5]:


class FlagsAsyncio:
    def __init__(self, data, url, dest_dir, *, verbose = True):
        self.base_url = url
        self.data = data
        self.dest_dir = dest_dir
        self.verbose = verbose
    
    # блокирующая операция вывода на диск
    def save_flag(self, img, cc):
        file_name = cc.lower() + '.gif'
        path = os.path.join(DEST_DIR, file_name) 
        with open(path, 'wb') as fp:
            fp.write(img)

    async def get_flag(self, session, cc):
        url = '{}/{cc}/{cc}.gif'.format(self.base_url, cc = cc.lower())
        async with session.get(url) as resp:
            return await resp.content.read()
    
    async def download_one(self, session, cc):
        image = await self.get_flag(session, cc)
        print(cc, end =' ')
        self.save_flag(image, cc)
        return cc
    
    async def download_many(self):
        async with aiohttp.ClientSession() as session:
            coros = [self.download_one(session, cc) for cc in sorted(self.data)]
            return await asyncio.wait(coros) # Wait for the Futures and coroutines given by fs to complete (неблокриующая)


def main(flags):
    loop = asyncio.new_event_loop()
    if flags.verbose: 
        start_time = time.time()    
    to_do = flags.download_many()
    res, _ = loop.run_until_complete(to_do)
    if flags.verbose: 
        print('\nDownloaded for {:.2f}'.format(time.time() - start_time))
    loop.close()
    return len(res)

if __name__ == '__main__':
    fa = FlagsAsyncio(*params)
    main(fa)


# In[11]:


CONCUR_REQ = 5


class FetchException(Exception):
    """Used for handling web exceptions and getting country code"""
    def __init__(self, country_code):
        self.country_code = country_code
        
        
class FlagsAsyncioErrorHandler(FlagsAsyncio):
    def __init__(self, *args, **kargs):
        self.statuses = {}
        self.concur_req = kargs['concur_req'] if 'concur_req' in kargs else 3
        super().__init__(*args, **kargs)
        
    async def get_flag(self, session, cc):
        """downloads a single flag using current session"""
        url = '{}/{cc}/{cc}.gif'.format(self.base_url, cc = cc.lower())
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.content.read()
            elif resp.status == 404:
                raise aiohttp.web.HTTPNotFound
            else: 
                raise aiohttp.http_exceptions.HttpProcessingError(code = resp.status, 
                                                                  message = resp.reason, headers = resp.headers)
                
    async def download_one(self, session, semaphore, cc):
        """saves img if download is successful"""
        try:
            async with semaphore: # asyncio.Semaphore limits the max of concurrences
                image = await self.get_flag(session, cc)
        except aiohttp.web.HTTPNotFound:
            msg = 'not found'
        except Exception as exc:
            raise FetchException(cc) from exc
        else:
            self.save_flag(img, cc)
            msg = 'ok'
            
        self.statuses[msg] = self.statuses.get(msg, 0) + 1
        if self.verbose: 
            print(cc, msg, end = '|')
        return cc
    
    async def download_many(self):
        """gets semaphore and creates connection """
        semaphore = asyncio.Semaphore(self.concur_req) # __aenter__ for .acquire(), __aexit__ for .release()
        async with aiohttp.ClientSession() as session:
            #self.data.append('error') # testing exceptions handling
            coros = [self.download_one(session, semaphore, cc) for cc in sorted(self.data[:1])]
            for future in asyncio.as_completed(coros): # returns an iterator for future objects
                try:
                    res = await future
                    print(res)
                except FetchException as exc:
                    country_code = exc.country_code
                    try:
                        error_msg = exc.__cause__.args[0] # if there is a msg in exception
                    except IndexError:
                        error_msg = exc.__cause__.__class__.__name__ # else get the name of initial exception
                    if self.verbose:
                        print('Error for %s:%s' % (country_code, error_msg))
                    self.statuses['error'] = self.statuses.get('error', 0) + 1
            
            
def main(flags):
    loop = asyncio.new_event_loop()
    if flags.verbose: 
        start_time = time.time()
        
    to_do = flags.download_many()
    print(to_do)
    res, _ = loop.run_until_complete(to_do)
    if flags.verbose: 
        print('\nDownloaded for {:.2f}'.format(time.time() - start_time))
    loop.close()
    return flags.statuses

if __name__ == '__main__':
    fa = FlagsAsyncioErrorHandler(*params)
    main(fa)

