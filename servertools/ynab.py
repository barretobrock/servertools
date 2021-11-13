import requests
from typing import (
    Dict,
    List
)


class YNAB:
    API_URL = 'https://api.youneedabudget.com/v1'

    def __init__(self, token: str):
        self.header = {'Authorization': f'Bearer {token}'}

    def _request(self, endpoint: str) -> requests.Response:
        resp = requests.get(f'{self.API_URL}{endpoint}', headers=self.header)
        resp.raise_for_status()
        return resp

    def get_budgets(self) -> List[Dict]:
        resp = self._request('/budgets')
        data = resp.json().get('data').get('budgets')
        return data

    def get_budget(self, budget_id: str) -> Dict:
        resp = self._request(f'/budgets/{budget_id}')
        data = resp.json().get('data').get('budget')
        return data
