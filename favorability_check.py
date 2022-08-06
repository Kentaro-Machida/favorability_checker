"""
前位処理済みのcsvファイルを読み込み
総合および、項目別のスコアJSON形式で出力する
"""

import pandas as pd
import numpy as np
import json
import re
import os
from dataclasses import dataclass

def dump_jsonl(data, output_path, append=False):
    """
    Write list of objects to a JSON lines file.
    """
    mode = 'a+' if append else 'w'
    with open(output_path, mode, encoding='utf-8') as f:
        for line in data:
            json_record = json.dumps(line, ensure_ascii=False)
            f.write(json_record + '\n')

def load_jsonl(input_path, has_index=True) -> list:
    """
    Read list of objects from a JSON lines file.
    """
    data = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if has_index:
                json_l = json.loads(line.rstrip('\n|\r'))
                # hack ... 
                v = list(json_l.values())[0]
                data.append(v)
            else:
                data.append(json.loads(line.rstrip('\n|\r')))
    return data

@dataclass
class FavorabilityGetter():
    output_json_path:str = "./socres/score.jsonl"
    input_csv_dir:str = "./processed_data"
    meta_path:str = "./meta_data/meta_data.jsonl"
    id:str = '0'

    def __post_init__(self):
        self.favorability = 0.0  # 脈ありスコア
        self.indifference = 0.0  # 脈なしスコア
        self.analysis_dict = {}  # 分析結果を辞書で保持
        self.analysis_dict['id'] = self.id
        self.input_file_name = "processed_" + str(self.id) +".csv"
        self.input_csv_path = os.path.join(self.input_csv_dir, self.input_file_name)
        self.df = pd.read_csv(self.input_csv_path)

        json_list = load_jsonl(self.meta_path, has_index=False)
        self.meta_dict = json_list[-1]

        self.analysis_dict['usr_name'] = self.meta_dict['usr_name']
        self.analysis_dict['target_name'] = self.meta_dict['target_name']

    def specify_period(self, period = 3):
        """
        最新の会話から何ヶ月前までを評価するかを選択する
        デフォルトでは3ヶ月前まで
        """
        self.df = self.df[
            self.df['unix_stamp'][len(self.df)-1] - (60*60*24*31*period) \
                < self.df['unix_stamp']
        ]
        self.df = self.df.reset_index()

    def get_pattern_match(self, regular_expression:str)->list:
        """
        受けとったパターンを探索してヒットしたらリストで返す
        """
        # スペースおよび改行を削除することで文字列を改行して書いてもヒットする
        regular_expression = regular_expression.replace('\ ', '')
        regular_expression = regular_expression.replace(' ', '')
        pattern = re.compile(regular_expression)

        pattern_list = []
        target_df = self.df[self.df['from'] == self.meta_dict['target_name']]
        for text in target_df['text']:
            if pattern.match(text):
               pattern_list.append(text)
        return pattern_list

    def str_count_check(self, search_str_list:list)->dict:
        """
        input: 合計で何メッセージの中に含まれているかを知りたい
        文字のリスト。e.g. ['?',"？" ]
        """
        output_dict = {}
        for name in self.df['from'].unique():
            count = 0
            parsonal_df = self.df[self.df['from'] == name]
            for text in parsonal_df['text']:
                for search_str in search_str_list:
                    if search_str in text:
                        count += 1
                        break
            output_dict[name] = count
        return output_dict

    def question_check(self, thresh=0.45)->dict:
        """
        双方の質問のバランスから脈あり、脈なしスコアに加算
        自分の方が多すぎる->脈なし
        同じくらいもしくは相手の方が多い->脈あり
        """
        usr_name = self.meta_dict['usr_name']
        target_name = self.meta_dict['target_name']

        quesition_count = self.str_count_check(["？", "?"])
        score = quesition_count[target_name]/ \
            (quesition_count[usr_name]+quesition_count[target_name]) - thresh

        if score > 0:
            self.favorability += score
        else:
            self.indifference += np.abs(score)
        
        self.analysis_dict["question"] = quesition_count

    def image_check(self):
        """
        画像が送信された割合
        脈ありスコアの加算のみを行う
        """
        image_count = self.str_count_check(["[写真]"])
        score = image_count[self.meta_dict['target_name']]/len(self.df)
        self.favorability += score

        self.analysis_dict["image"] = image_count

    def url_check(self):
        """
        urlが送信された割合
        脈ありスコアの加算のみを行う
        """
        image_count = self.str_count_check(["http"])
        score = image_count[self.meta_dict['target_name']]/len(self.df)
        self.favorability += score

        self.analysis_dict["image"] = image_count

    def conversation_density_check(self, day=14):
        """
        やり取りの密度が高いほど脈ありスコアを加算
        やり取りの多さは人によって異なるため、密度が低いことによる
        脈なしスコアの加算は行わない.デフォルト期間は2週間
        e.g. 1日あたり3回相手からメッセージが来てたら0.3追加
        """
        target_day_df = self.df[
            self.df['unix_stamp'][len(self.df)-1] - day*24*60*60\
                < self.df['unix_stamp']
        ]
        # 1日に平均して何回相手からメッセージが来ているか
        density = sum(target_day_df['from'] == self.meta_dict["target_name"]) / day  # 1日あたりのやり取り回数
        score = density/10
        self.favorability += score

        self.analysis_dict["message_count_per_day"] = density

    def string_length_check(self):
        """
        双方のメッセージの長さのバランスおよび、相手の長さを評価する。
        相手が長くて、自分は短い -> バランスが悪くても脈アリ加点
        自分が長くて、相手は短い -> バランスが悪ければ脈なし加点
        """
        def get_length(text):
            return len(text)

        length_dict = {}
    
        usr_df = self.df[self.df['from'] == self.meta_dict['usr_name']]
        usr_mean = usr_df['text'].map(get_length).mean()
        length_dict[self.meta_dict['usr_name']] = usr_mean
        
        target_df = self.df[self.df['from'] == self.meta_dict['target_name']]
        target_mean = target_df['text'].map(get_length).mean()
        length_dict[self.meta_dict['target_name']] = target_mean

        self.analysis_dict['length'] = length_dict

        diff = usr_mean - target_mean
        if diff > 0:
            if diff > 10:
                self.indifference += diff/100
            else:
                self.favorability += 0.3*(10-diff)/9
        else:
            if -diff < 10:
                self.favorability += 0.3
            else:
                self.favorability += 0.5

    def conversation_count_check(self, thresh=0.4):
        """
        会話量のバランスを評価する。
        もし、自分の方がメッセージを送りすぎていたら脈なしスコアが上昇
        相手のほうから多く来ていれば、脈ありスコア上昇
        """
        usr_name = self.meta_dict['usr_name']
        target_name = self.meta_dict['target_name']
        name_count_dict = {}
        for name in self.df['from'].unique():
            name_count_dict[name] = sum(self.df['from']==name)

        score = name_count_dict[target_name] / \
            (name_count_dict[usr_name] + name_count_dict[target_name]) - thresh
        
        if score > 0:
            self.favorability += score
        else:
            self.indifference += np.abs(score)

        self.analysis_dict['message_count'] = name_count_dict

    def call_check(self, added_score=0.5):
        """
        電話をしたことがあるかを確認する
        相手から来ていたら0.5、自分からしていたら0.25
        通話30分ごとに2倍、3倍としていく(後で実装)
        """
        score = 0
        for text in self.df["text"]:
            if "通話時間" in text:
                score = added_score
        call_count = self.str_count_check(["通話時間"])
        self.favorability += score
        self.analysis_dict['call'] = call_count

    def lovers_check(self, added_score=10, full_score_length=1)->int:
        """
        相手に恋人がいるかどうかの確認が行われているかどうかを評価する。
        脈ありなテキストは他のスコア算出とは独立させる。
        """
        pattern_text = ".*(彼氏|彼女|恋人|彼|好きな人|すきな人|気になる人)\
            .*(いる|いつ|いない|います).*(\?|？).*"
        
        lovers_check_list = self.get_pattern_match(pattern_text)
        self.analysis_dict["lovers_check"] = lovers_check_list
        if len(lovers_check_list) >= full_score_length:
            return added_score
        else:
            return 0

    def asking_date_check(self, added_score=10, full_score_length=3):
        """
        デート的なものに誘われたものを探す
        """
        # 疑問型のお誘い
        pattern_text = ".*(い|行).*\
            (かん|きません|かない|どう|どお|みん|みない|ちゃう).*(\?|？).*"

        matched_list = self.get_pattern_match(pattern_text)
        # letsタイプのお誘い
        pattern_text = ".*(見に|食べ|しに|のみ|飲み|呑み).*\
            (よう|こう|ましょう|いこ|行こ)"
        matched_list.extend(self.get_pattern_match(pattern_text))
        self.analysis_dict['asking_date'] = matched_list
        if len(matched_list) >= full_score_length:
            return added_score
        else:
            return added_score * len(matched_list) / full_score_length

    def conversation_start_check(self, thresh=0.4):
        """
        会話を始めた方のバランスを評価する
        相手から会話を始めてきた方が多ければ評価
        自分があまりにも多すぎると減点
        """
        talk_start = {}
        target = self.meta_dict['target_name']
        usr = self.meta_dict['usr_name']

        talk_start[usr] = int(self.df[self.df['from'] == usr]['start_talk'].sum())
        talk_start[target] = int(self.df[self.df['from'] == target]['start_talk'].sum())

        score = (talk_start[target]/(talk_start[usr] + talk_start[target])) - thresh

        if score > 0:
            self.favorability += score
        else:
            self.indifference += -score
        self.analysis_dict['talk_start_count'] = talk_start

    def interval_balance_check(self, thresh=0.5):
        """
        会話間の空き時間のバランスを評価する。
        相手が早い分には評価し、あまりにも自分が早い場合、
        脈なしとする。
        """
        interval_mean_dict = {}
        usr_name = self.meta_dict['usr_name']
        target_name = self.meta_dict['target_name']

        usr_df = self.df[self.df['from'] == usr_name]
        target_df = self.df[self.df['from'] == target_name]

        usr_interval = float(usr_df[usr_df['interval[h]'] != 0]['interval[h]'].mean())
        target_interval = float(target_df[target_df['interval[h]'] != 0]['interval[h]'].mean())

        interval_mean_dict[usr_name] = usr_interval
        interval_mean_dict[target_name] = target_interval

        score = (target_interval / (usr_interval + target_interval)) - thresh

        if score > 0:
            self.favorability += score
        else:
            self.indifference += -score

        self.analysis_dict['interval_average'] = interval_mean_dict

    def all_caluculate(self):
        self.specify_period(36)
        self.question_check()
        self.conversation_count_check()
        self.conversation_density_check()
        self.string_length_check()
        self.call_check()
        self.conversation_start_check()
        self.interval_balance_check()
        lovers_addition = self.lovers_check()
        date_addition = self.asking_date_check()
        
        self.analysis_dict['favorability'] = self.favorability
        self.analysis_dict['indifference'] = self.indifference
        self.analysis_dict['total_score'] = int(80*np.exp(self.favorability)\
            /(np.exp(self.favorability) + np.exp(self.indifference))
        ) + lovers_addition + date_addition

        output_json_path = './score_output/score.jsonl'
        json_list = load_jsonl(output_json_path, has_index=False)
        json_list.append(self.analysis_dict)
        dump_jsonl(json_list, output_json_path, append=False)
        return self.analysis_dict

def test():
    getter = FavorabilityGetter(id = "0")
    getter.specify_period(36)
    getter.question_check()
    getter.conversation_count_check()
    getter.conversation_density_check()
    getter.string_length_check()
    getter.call_check()
    getter.lovers_check()
    getter.conversation_start_check()
    getter.interval_balance_check()
    getter.asking_date_check()
    
    getter.analysis_dict['favorability'] = getter.favorability
    getter.analysis_dict['indifference'] = getter.indifference
    getter.analysis_dict['total_score'] = int(100*np.exp(getter.favorability)\
        /(np.exp(getter.favorability) + np.exp(getter.indifference))
    )
    
    print("+",getter.favorability)
    print("-",getter.indifference)
    print(getter.analysis_dict)

    output_json_path = './score_output/score.jsonl'
    json_list = load_jsonl(output_json_path, has_index=False)
    json_list.append(getter.analysis_dict)
    dump_jsonl(json_list, output_json_path, append=False)
if __name__=='__main__':
    test()