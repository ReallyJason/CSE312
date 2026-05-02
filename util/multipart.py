class Multipart:
    def __init__(self, boundary, parts):
        self.boundary=boundary
        self.parts=parts

class Multipp:
    def __init__(self, headers, name, content):
        self.headers=headers
        self.name=name
        self.content=content

def get_boundary(b):
    boundary={}
    for bound in b.split(";"):
        bound = bound.strip()
        if "=" in bound:
            key, value = bound.split("=", 1)
            key=key.split("\r\n")[0].strip()
            value=value.split("\r\n")[0].strip()
            boundary[key] = value
    return boundary["boundary"]

def get_headers(start):
    start=start.decode("utf-8")
    l=start.split("\r\n")
    headers={}

    for line in l:
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers

def get_cd(cd):
    cdsi = {}
    for cds in cd.split(";"):
        cds = cds.strip()
        if "=" in cds:
            key, value = cds.split("=", 1)
            key = key.split("\r\n")[0].strip()
            value = value.split("\r\n")[0].strip()
            if value.startswith('"') and value.endswith('"') and len(value)>=2:
                value = value[1:-1]
            cdsi[key] = value
    return cdsi["name"]


def parse_multipart(request):
    h=request.headers
    boundary=get_boundary(h["Content-Type"])
    actual_boundary=b"--"+boundary.encode('utf-8') #get boundary

    body=request.body
    pt=body.split(actual_boundary) #spliting every bound into parts

    parts=[]

    for i, p in enumerate(pt):
        if i==0:
            continue
        if p.startswith(b"--"): #bound ends with -- means final
            break
        if p.startswith(b'\r\n'):
            p=p[2:]

        crlfcrlf_index=p.find(b'\r\n\r\n')

        start=p[:crlfcrlf_index] #before header
        rest=p[crlfcrlf_index+4:]
        if rest.endswith(b'\r\n'):
            content=rest[:-2]
        else:
            content=rest

        headers=get_headers(start)

        content_disposition=headers.get("Content-Disposition")
        name=get_cd(content_disposition)


        parts.append(Multipp(headers=headers, name=name, content=content))

    return Multipart(boundary=boundary, parts=parts)