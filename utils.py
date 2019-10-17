from typing import Union, Iterable

from config import w3


def get_logs(
        address: str,
        topics: Union[Iterable[Union[Iterable[str], str]], str],
        from_block: int = 0,
        to_block: int = 'latest'
) -> list:
    return w3.eth.getLogs({
        'fromBlock': from_block,
        'toBlock': to_block,
        'address': address,
        'topics': topics
    })
