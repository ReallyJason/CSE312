import json


class Response:
    def __init__(self):
        self.code=200
        self.texts="OK"
        self.head={"X-Content-Type-Options": "nosniff"}
        self.cook=[]
        self.body=b""

    def set_status(self, code, text):
        self.code=code
        self.texts=text
        return self

    def headers(self, headers):
        for key,value in headers.items():
            self.head[key.strip()]=value.strip()
        return self

    def cookies(self, cookies):
        for key,value in cookies.items():
            self.cook.append(f"{key.strip()}={value.strip()}")
        return self

    def bytes(self, data):
        self.body+=data
        return self

    def text(self, data):
        self.body+=data.encode('utf-8')
        return self

    def json(self, data):
        self.head["Content-Type"]="application/json"
        self.body=json.dumps(data).encode('utf-8')
        return self

    def to_data(self):
        if "Content-Type" not in self.head:
            self.head["Content-Type"]="text/plain; charset=utf-8"
        self.head["Content-Length"]=str(len(self.body))

        responses = ["HTTP/1.1 "+str(self.code)+" "+self.texts]
        for k,v in self.head.items():
            responses.append(str(k)+": "+str(v))
        for cookie in self.cook:
            responses.append("Set-Cookie: "+cookie)

        formatted_response="\r\n".join(responses)+"\r\n\r\n"
        return formatted_response.encode("utf-8")+self.body


def test1():
    res = Response()
    res.text("hello")
    expected = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 5\r\n\r\nhello'
    actual = res.to_data()
    print(expected==actual)
    #print(expected)
    #print(actual.decode())

if __name__ == '__main__':
    test1()
