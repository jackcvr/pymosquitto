class TopicMatcher:
    class Node:
        __slots__ = ("children", "value")

        def __init__(self):
            self.children = {}
            self.value = None

    def __init__(self, lock=None):
        self._root = self.Node()
        self._lock = lock
        if not lock:
            from contextlib import nullcontext

            self._lock = nullcontext()

    def __setitem__(self, key, value):
        with self._lock:
            node = self._root
            for sym in key.split("/"):
                node = node.children.setdefault(sym, self.Node())
            node.value = value

    def __getitem__(self, key):
        with self._lock:
            try:
                node = self._root
                for sym in key.split("/"):
                    node = node.children[sym]
                if node.value is None:
                    raise KeyError(key)
                return node.value
            except KeyError as e:
                raise KeyError(key) from e

    def __delitem__(self, key):
        with self._lock:
            lst = []
            try:
                parent, node = None, self._root
                for k in key.split("/"):
                    parent, node = node, node.children[k]
                    lst.append((parent, k, node))
                node.value = None
            except KeyError as e:
                raise KeyError(key) from e
            else:  # cleanup
                for parent, k, node in reversed(lst):
                    if node.children or node.value is not None:
                        break
                    del parent.children[k]

    def find(self, topic):
        lst = topic.split("/")
        normal = not topic.startswith("$")

        def rec(node, i=0):
            if i == len(lst):
                if node.value is not None:
                    yield node.value
            else:
                part = lst[i]
                if part in node.children:
                    for value in rec(node.children[part], i + 1):
                        yield value
                if "+" in node.children and (normal or i > 0):
                    for value in rec(node.children["+"], i + 1):
                        yield value
            if "#" in node.children and (normal or i > 0):
                value = node.children["#"].value
                if value is not None:
                    yield value

        with self._lock:
            return rec(self._root)
