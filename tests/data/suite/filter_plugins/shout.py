class FilterModule:
    def filters(self):
        return {"shout": lambda s: str(s).upper() + "!"}
