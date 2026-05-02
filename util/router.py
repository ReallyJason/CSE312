from util.response import Response

class Router:

    def __init__(self):
        self.routes=[]

    def add_route(self, method, path, action, exact_path=False):
        self.routes.append((method, path, action, exact_path))

    def route_request(self, request, handler):
        matched = False

        for method, path, action, exact_path in self.routes:
            if request.method != method:
                continue
            if exact_path:
                if request.path==path:
                    action(request,handler)
                    matched=True
            else:
                if request.path[:len(path)]==path:
                    action(request, handler)
                    matched=True
        if not matched:
            body = "The requested content does not exist"

            res = Response()
            res.set_status(404, "Not Found")
            res.headers({
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Length": str(len(body)),
                "X-Content-Type-Options": "nosniff"
            })
            res.text(body)
            handler.request.sendall(res.to_data())
