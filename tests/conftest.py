import os

# fixture stubs stand in for missing GPU libraries only inside tests
os.environ.setdefault("TAGWERK_STUBS", "1")
