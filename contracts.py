import json

from web3._utils.events import get_event_data

from config import w3, BNT_ADDRESS


class Contract:
    def __init__(self, abi_path, address):
        with open(abi_path) as fh:
            self.contract = w3.eth.contract(abi=json.load(fh), address=address)

    def parse_event(self, event_type: str, event: dict) -> dict:
        return get_event_data(w3.codec, self.contract.events[event_type]._get_event_abi(), event)


class BancorConverter(Contract):
    def __init__(self, address):
        super().__init__('abi/BancorConverter.abi', address)

    def token_address(self) -> str:
        return self.contract.functions.connectorTokens(1).call()

    def token_balance(self, token_address: str) -> int:
        return self.contract.functions.getConnectorBalance(token_address).call()

    def price(self, token_address: str = None) -> float:
        if not token_address:
            token_address = self.token_address()
        return self.token_balance(BNT_ADDRESS) / self.token_balance(token_address)


class ERC20(Contract):
    def __init__(self, address):
        super().__init__('abi/ERC20.abi', address)

    def decimals(self) -> int:
        return self.contract.functions.decimals().call()
