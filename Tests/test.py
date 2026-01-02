class Emitter:
    def __init__(self, socket):
        self.s = socket
        self.body = {}
        self.cluster_id = ""
        
        self.status = True
        self.error = None

    def init_(self, cluster_id: str, body: dict) -> None: #Clear typing later.
        self.body, self.cluster_id = body, cluster_id
        return self

    def broadcast(self, event: str, status: bool = True, error: str | None = None):
        if not self.body or self.cluster_id == "":
            raise("Can't broadcast, either body or cluster_id are not provided") 
        self.status, self.error = True, None
        print(self.body, self.s, self.cluster_id)
        return self

    def close(self):
        self.status, self.error = True, None
        print("JIDIWDHIHIHDHIEIHIDFHE")
        return self

    def done(self):
        return self.status, self.error

emt = Emitter("43456364653")
print(emt.init_("gdygdgygdye", {"ieiueui": 937828473}).broadcast("aaaaaa", True).close().done())