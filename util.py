"""
Common auxiliary functions for data mining, feature engineering, file IO .etc
"""
import numpy as np
import tushare as ts 
import pandas as pd
from keras.utils import to_categorical
import os
import sys
import re
import chardet
from multiprocessing import Pool
import logging
logging.basicConfig(filename='logger.log', level=logging.INFO)


# project_path = os.path.abspath('util.py').split(os.sep)[:-1]
# project_path = os.sep.join(project_path)
project_path = r'E:\\DX'


class StockRawData:
    @staticmethod
    def get_stock_data(stock: str, start_date: str, end_date: str):
        """
        获取指定股票指定时间段的历史交易数据
        :param stock: 股票代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 历史数据DataFrame
        """
        if os.path.exists(os.path.join(project_path, r'Data\{}.csv'.format(stock))):
            print("{} File already exists".format(stock))
            return None
        else:
            try:
                # print("Begin download")
                df = ts.get_k_data(stock, start=start_date, end=end_date)
                stock_code = df.code.values[0]
                df.index = df.iloc[:, 0]
                del df.index.name
                df = df.drop(labels=['code', 'date'], axis=1)
                df.columns = pd.MultiIndex.from_product([[stock_code], df.columns], names=['code', 'data'])
                df.to_csv(os.path.join(project_path, r'Data\{}.csv'.format(stock)))
                return df
            except AttributeError:
                print("{} is down during this period of time".format(stock))
                return None

    @staticmethod
    def get_universe()->pd.DataFrame:
        """
        Get universe of today hs300s
        :return: list
        """
        today_universe = ts.get_hs300s()
        # top_universe = today_universe[today_universe['weight'] > today_universe['weight'].quantile(0.6)]
        return today_universe

    @staticmethod
    def get_universe_data(universe: list, start_date: str, end_date: str)->list:
        """
        多进程获取所有股票历史数据
        :param universe: 股票池列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 历史数据DataFrame
        """
        try:
            pool = Pool(6)
            params = zip(universe, [start_date]*len(universe), [end_date]*len(universe))
            result = pool.starmap(StockRawData.get_stock_data, params)
            result = list(filter(None, result))
            result_df = pd.concat(result, axis=1)
            # result_df.index = result_df.iloc[:, 0]
            # result_df = result_df.drop(labels='date', axis=1, level=1)
            return result
        except ValueError:
            print("All stock data has been downloaded, load local data")
            local_root_path = os.path.join(project_path, r'Data')
            result = list()
            for root, dirs, files in os.walk(local_root_path):
                for file in files:
                    file_path = os.path.join(local_root_path, file)
                    # print(file_path)
                    df = pd.read_csv(file_path, index_col=0, header=[0, 1])
                    result.append(df)
            return result

    @staticmethod
    def rolling_sampling(raw_data, window=10):
        """
        Rolling through the whole dataframe of a single stock with a fixed window of single stock to sample data for training and test
        :return: list of tuple(X,y)
        """
        all_feature = []
        all_output = []

        def func(stock_data: pd.DataFrame):
            for i in range(0, stock_data.shape[0] - window - 1):
                feature = stock_data.iloc[i:i + window, :]
                output = stock_data.loc[stock_data.index[i + window], (slice(None), 'close')]
                all_feature.append(feature)
                all_output.append(output)
        [func(item) for item in raw_data if item.shape[0] == 94]
        return all_feature, all_output


class FatureEngineering:
    @staticmethod
    def feature_label_split(raw_data: list)->tuple:
        """
        Split feature and label from raw data, for the use of Keras model
        :return:X , encoded_y
        """
        X = np.array([item.values[0:10, :] for item in raw_data if item.shape[0] >= 20])
        y_all = np.array([item.loc[item.index[11], (slice(None), 'close')] for item in raw_data if item.shape[0] >= 20] )
        y = (y_all > np.mean(y_all))*1
        encoded_y = to_categorical(y, num_classes=2)
        return X, encoded_y

    @staticmethod
    def feature_label_split_tf(raw_data: list)->tuple:
        """
        Split feature and label from raw data, for the use of tensorflow model
        :return:
        """
        # raw_data = self.__get_raw_data()
        # print(raw_data[0].shape)
        X = np.array([item.values[0:10, :] for item in raw_data if item.shape[0] >= 20])
        X_T = X.transpose((1, 0, 2))
        y_all = np.array([item.loc[item.index[11], (slice(None), 'close')] for item in raw_data if item.shape[0] >= 20] )
        y = (y_all > np.mean(y_all))*1
        encoded_y = to_categorical(y, num_classes=2)
        return X_T, encoded_y

class DataIO:
    @staticmethod
    def detect_encode_style(file_path):
        with open(file_path, 'rb') as f:
            lines = f.readlines()
            res = chardet.detect(lines[0])
            encoding = res['encoding']
        return encoding

    @staticmethod
    def get_descendant_file_path(parent_path):
        """
        Load descendant file of certain directory
        """
        csv_relative_path = []
        for root, dirs, files in os.walk(parent_path):
            for file in files:
                words = file.split(r'.')
                if words[-1] == 'csv':
                    file_path = os.path.join(parent_path, file)
                    csv_relative_path.append(file_path)
        return csv_relative_path

    @staticmethod
    def load_data(parent_path):
        csv_file_path = DataIO.get_descendant_file_path(parent_path)
        df_all = []
        for path in csv_file_path:
            df = pd.read_csv(path, sep=r'\t', encoding='UTF-16', skipinitialspace=True, engine='python')
            df_all.append(df)
        res_df = pd.concat(df_all, axis=0)
        pd.to_pickle(res_df, path='stock_daily_price.pkl')
        return res_df


if __name__ == "__main__":
    universe = StockRawData.get_universe()
    res = StockRawData.get_universe_data(list(universe.code), start_date='2018-01-03', end_date='2018-05-26')
    # re = get_stock_data('600000', start_date='2018-01-03', end_date='2018-05-26')
    # X, X_T, y, encoded_y = FatureEngineering.feature_label_split_tf(res)
    all_date = StockRawData.rolling_sampling(res, 10)
    print(None)