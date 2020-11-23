# -*- coding: utf-8 -*-
""" Mozilla Hubs room """
import requests
from bs4 import BeautifulSoup

class Room:
    """
    A class represents a hubs room.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self.reticulum_server = self.__get_reticulum_server(url)
        self.hub_id = self.__get_hub_id(url)

    def get_reticulum_server(self) -> str:
        """
        Returns reticulum server name for this room.

        Returns:
            str: reticulum server name
        """
        return self.reticulum_server

    def get_hub_id(self) -> str:
        """
        Returns hub_id for this room.

        Returns:
            str: hub_id
        """
        return self.hub_id

    def get_url(self) -> str:
        """
        Returns URL for this room.

        Returns:
            str: room URL
        """
        return self.url

    @staticmethod
    def __get_reticulum_server(url: str) -> str:
        """
        Returns reticulum server name for this client.

        Args:
            url(str): mozilla hubs room's URL.

        Returns:
            str: reticulum server name
        """
        try:
            resp = requests.get(url)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

        host = None
        soup = BeautifulSoup(resp.text, 'lxml')
        for meta in soup.findAll("meta"):
            meta_name = meta.get('name', '').lower()
            if meta_name == 'ret:phx_host':
                host = meta.get('value', '').lower()
                break
        return host

    @staticmethod
    def __get_hub_id(url: str) -> str:
        """
        Extracts hub_id from the given mozilla hubs URL.

        Args:
            url(str): mozilla hubs room's URL.

        Returns:
            str: hub_id
        """
        if url.startswith('https://hubs.mozilla.com/') is False:
            raise ValueError("Incorrect mozilla hubs URL.")

        path = url[len('https://hubs.mozilla.com/'):]
        return path.split("/")[0]

if __name__ == '__main__':
    room = Room("https://hubs.mozilla.com/jccsqWd/tec-j-annual-poster-room-1")
    print(room.get_reticulum_server())
    print(room.get_hub_id())
    print(room.get_url())
