import typing as t
import threading


class _Node:
    __slots__ = ("children", "value")

    def __init__(self) -> None:
        self.children: t.Dict[str, _Node] = {}
        self.value: t.Any = None


class TopicMatcher:
    def __init__(self) -> None:
        self._root = _Node()

    def __setitem__(self, key: str, value: t.Any) -> None:
        node = self._root
        for sym in key.split("/"):
            node = node.children.setdefault(sym, _Node())
        node.value = value

    def __getitem__(self, key: str) -> None:
        try:
            node = self._root
            for sym in key.split("/"):
                node = node.children[sym]
            if node.value is None:
                raise KeyError(key)
            return node.value
        except KeyError as e:
            raise KeyError(key) from e

    def __delitem__(self, key: str) -> None:
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

    def find(self, topic: str) -> t.Iterable[t.Any]:
        lst = topic.split("/")
        normal = not topic.startswith("$")

        def rec(node: _Node, i: int = 0):
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

        return rec(self._root)


class SafeTopicMatcher(TopicMatcher):
    def __init__(self, lock: threading.Lock = None) -> None:
        super().__init__()
        self._lock = lock or threading.RLock()

    def __setitem__(self, key: str, value: t.Any) -> None:
        with self._lock:
            super().__setitem__(key, value)

    def __getitem__(self, key: str) -> t.Any:
        with self._lock:
            return super().__getitem__(key)

    def __delitem__(self, key: str) -> None:
        with self._lock:
            super().__delitem__(key)

    def find(self, topic: str) -> t.List[t.Any]:
        with self._lock:
            return list(super().find(topic))
