"""Bounded allowlisted HTTPS imports, with DNS resolution pinned to public IPs."""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
import time
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from fastapi import HTTPException


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname, address, timeout):
        super().__init__(hostname,443,timeout=timeout,context=ssl.create_default_context())
        self.address=address

    def connect(self):
        raw=socket.create_connection((self.address,443),self.timeout)
        try:
            self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def validate_import_url(url,allowed_hosts):
    try:
        parsed=urlsplit(url)
        host=(parsed.hostname or '').lower()
        if (parsed.scheme!='https' or not host or parsed.username or parsed.password or
            parsed.port not in {None,443} or parsed.query or parsed.fragment or
            host not in allowed_hosts or any(ord(ch)<33 for ch in url) or '\\' in url):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()
        decoded=unquote(parsed.path)
        if any(ord(ch)<32 for ch in decoded):raise ValueError()
    except ValueError:
        raise HTTPException(422,'Use a permitted HTTPS hostname on port 443 without credentials, query secrets, or fragments.') from None
    try:
        records=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        addresses=list(dict.fromkeys(row[4][0] for row in records))
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise HTTPException(422,'URL resolves to a non-public destination.')
    except (OSError,ValueError):
        raise HTTPException(422,'URL hostname could not be safely resolved.') from None
    return parsed,addresses[0]


def fetch_import(url,config):
    allowed={host.strip().lower() for host in config.import_allowed_hosts.split(',') if host.strip()}
    parsed,address=validate_import_url(url,allowed)
    connection=PinnedHTTPSConnection(parsed.hostname,address,timeout=15)
    deadline=time.monotonic()+25
    try:
        connection.request('GET',parsed.path or '/',headers={'Accept':'text/csv, application/json','Accept-Encoding':'identity','User-Agent':'CTI-v5-import/1.0'})
        response=connection.getresponse()
        if 300<=response.status<400:
            raise HTTPException(422,'Redirects are not followed. Supply the final allowlisted HTTPS source URL.')
        if response.status!=200:
            raise HTTPException(502,'Source server did not return a successful response.')
        if response.getheader('Content-Encoding','identity').lower() not in {'identity',''}:
            raise HTTPException(422,'Compressed HTTP responses are not accepted for bounded imports.')
        length=response.getheader('Content-Length')
        if length:
            try:
                if int(length)<0 or int(length)>config.max_upload_bytes:raise ValueError()
            except ValueError:
                raise HTTPException(413,'Source content length exceeds the allowed limit.') from None
        chunks=[]
        total=0
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise HTTPException(504,'Source download exceeded the time limit.')
            if getattr(connection,'sock',None) is not None:
                connection.sock.settimeout(min(15,remaining))
            # read1 returns after one network read, so a slow trickle cannot
            # repeatedly reset the socket timeout while filling a 64KB read.
            reader=getattr(response,'read1',response.read)
            block=reader(min(65536,config.max_upload_bytes-total+1))
            if not block:break
            total+=len(block)
            if total>config.max_upload_bytes:raise HTTPException(413,'Source response exceeds the configured import limit.')
            chunks.append(block)
        raw=b''.join(chunks)
        filename=PurePosixPath(parsed.path).name or 'import.csv'
        canonical=None
        media=response.getheader('Content-Type','').split(';')[0].lower()
        if filename.lower().endswith('.json') or media=='application/json':
            try:
                from .tabular_import import json_frame
                canonical=json_frame(raw)
                filename='import.json'
            except (ValueError,TypeError):
                raise HTTPException(422,'JSON imports require a nonempty array of flat study records. Use the registry importer for ClinicalTrials.gov API responses.') from None
        elif not filename.lower().endswith('.csv') and media not in {'text/csv','application/csv'}:
            raise HTTPException(422,'URL imports accept CSV or flat JSON records only.')
        else:
            filename='import.csv'
        return raw,filename,canonical
    except (OSError,ssl.SSLError,http.client.HTTPException):
        raise HTTPException(502,'Source download failed. Check URL availability and TLS.') from None
    finally:
        connection.close()
