import logging

import openapi_client
from openapi_client.rest import ApiException


class DataSourceMeta(type):

    def __instancecheck__(self, instance):
        return self.__subclasscheck__(type(instance))

    def __subclasscheck__(self, subclass):
        return (hasattr(subclass, 'get_record') and
                callable(subclass.get_record) and
                hasattr(subclass, 'get_records_count') and
                callable(subclass.get_records_count) and
                hasattr(subclass, 'get_records') and
                callable(subclass.get_records))


class DataSourceInterface(metaclass=DataSourceMeta):
    pass


class BaseDataSource(DataSourceInterface):
    _cache = None

    def __new__(cls, **kwargs):
        cls._cache = []
        return cls

    @classmethod
    def get_records(cls) -> list:
        pass

    @classmethod
    def get_record(cls, index: int) -> object:
        if len(cls._cache) == 0:
            raise ValueError('empty data source')
        if index > len(cls._cache):
            raise ValueError('index is greater then records count')
        return cls._cache[index]

    @classmethod
    def get_records_count(cls) -> int:
        if len(cls._cache) == 0:
            cls._cache = cls.get_records()
        return len(cls._cache)


class OpenApiDataSource(BaseDataSource):

    def __new__(cls, host: str, access_token: str, *args, **kwargs):
        cls._host = host
        cls._token = access_token
        return super().__new__(cls)

    @classmethod
    def init_api_client(cls) -> openapi_client.ApiClient:
        configuration = openapi_client.Configuration(
            host=cls._host
        )
        configuration.access_token = cls._token
        return openapi_client.ApiClient(configuration)


class TransactionDataSource(OpenApiDataSource):

    def __new__(cls, host: str, access_token: str, user_id: int):
        cls._user_id = user_id
        return super().__new__(cls, host, access_token)

    @classmethod
    def get_records(cls) -> list:
        with cls.init_api_client() as api_client:
            api_instance = openapi_client.TransactionsApi(api_client)
            try:
                api_response = api_instance.transaction_log(cls._user_id)
                return api_response
            except ApiException as e:
                logging.error("Exception when calling ResidentsApi->list_residents: %s" % e)
        return []


class ResidentDataSource(OpenApiDataSource):

    @classmethod
    def get_records(cls) -> list:
        with cls.init_api_client() as api_client:
            api_instance = openapi_client.ResidentsApi(api_client)
            limit = 100
            offset = 0
            try:
                api_response = api_instance.list_residents(limit=limit, offset=offset)
                return api_response
            except ApiException as e:
                logging.error("Exception when calling ResidentsApi->list_residents: %s" % e)
        return []


class CsvDataSource(BaseDataSource):

    def __new__(cls, filepath: str, sep: str, *args, **kwargs):
        f = open(filepath, "r")
        content = f.read().replace('\r', '')
        lines = content.split('\n')
        cls._cache = []
        for line in lines:
            row = line.split(sep)
            if len(row) > 0:
                cls._cache.append(row)
        return cls

    @classmethod
    def get_records(cls) -> list:
        return cls._cache
