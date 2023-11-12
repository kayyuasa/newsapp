#ライブラリをimport
import streamlit as st
from PIL import Image #イメージを表示
import time #ロード中の表示画面いれる
import pandas as pd
from datetime import datetime, timedelta# 現在時刻などの時間を扱う機能をインポート
from newsapi import NewsApiClient  #News APIから記事情報を取得
import openai #ChatGPTでの翻訳機能
import os # 環境ファイルからAPI KEYを指定
from dotenv import load_dotenv
import requests #Web記事のスクレイピング
from bs4 import BeautifulSoup
from PIL import Image

# .envファイルのパスを指定して読み込む
load_dotenv('.env')
NEWS_API_KEY =  os.getenv('NEWS_API_KEY') #環境変数を使用
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') #環境変数を使用


#<ニュースデータを取得し、Webページ掲出用に加工する>------ここから

#<条件設定> キーワード：辞書形式（今回はAIのみ）
set_keyword_list = {
    "AI" : "AI"
}

#<条件設定> ソース：辞書形式（今回はBBCのみ）
set_domains_list = {
    "BBC" : 'bbc.co.uk,bbc.com',
}

#<条件設定> 日時：本日から直近5日以内
date_to = datetime.now().date()
date_from_param = date_to - timedelta(days=5)

#<条件設定> キーワード・ソースのデフォルト値を設定
if 'set_domains' not in st.session_state:
    st.session_state.set_keyword = "AI"  # デフォルトをAIにしておく
    st.session_state.set_domains = "BBC"  # デフォルトをBBCにしておく
    st.session_state.article_blank = None  # Trueの時のみ、記事の取得、タイトルの翻訳を行う 
    st.session_state.index_japanese_title_pair_list = [None]  # 選択した記事、デフォルトを[None]にしておく


# NEWS APIで、条件設定で絞ったニュースデータを取得（日時、タイトル、コンテンツ、URL）
def get_articles(keyword, domains, date_from_param, date_to):
    # Init
    newsapi = NewsApiClient(api_key=NEWS_API_KEY)

    all_articles = newsapi.get_everything(q=keyword,
                                        #sources='bbc-news',
                                        domains=domains,
                                        from_param=date_from_param,
                                        to=date_to,
                                        language='en',
                                        #sort_by='relevancy',
                                        #page=2
                                        )

    # データフレーム作成
    data_articles = pd.DataFrame(columns=['日時', 'タイトル', 'コンテンツ', 'URL'])
    for i in range(len(all_articles['articles'])):
        _d = pd.DataFrame()
        _d['日時'] = [all_articles['articles'][i]['publishedAt'][:10]]
        _d['タイトル'] = [all_articles['articles'][i]['title']]
        _d['コンテンツ'] = [all_articles['articles'][i]['description']]
        _d['URL'] = [all_articles['articles'][i]['url']]
        data_articles = pd.concat([data_articles, _d], ignore_index=True)

    return data_articles

# タイトルを日本語に翻訳
def transrate_title_to_japanese(content_text_to_gpt):
    
    openai.api_key = OPENAI_API_KEY
    
    request_to_gpt = "以下の英語の記事のタイトルを日本語に翻訳してください" + content_text_to_gpt
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": request_to_gpt},
        ],
    )

    output_content = response.choices[0]["message"]["content"].strip()
    return output_content

# "日本語タイトル"のコラムを新規に作成して追加
def add_japanese_column(data_articles):

    _list = []
    for i in range(len(data_articles)):
        # タイトルを日本語に翻訳
        output_japanese_title = transrate_title_to_japanese(data_articles["タイトル"][i])
        # 翻訳されたタイトルをリストに追加
        _list.append(output_japanese_title)

    # "日本語タイトル"を新規に作成してリストを入れる
    data_articles.loc[:, "日本語タイトル"] = _list  # .locを使って、明示的にdata_articlesを直接変更したつもりだが、 SettingWithCopyWarningが消えない
    
    return data_articles

#<ニュースデータを取得し、Webページ掲出用に加工する>------ここまで


#<Streamlitでフロント画面を作成>------ここから

st.title("海外ニュース翻訳アプリ") # タイトル

image = Image.open('newspaperimage.jpg') #新聞画像挿入
st.image(image, caption=None)

st.markdown("気になる記事を選択すると、内容を確認できます")

st.sidebar.header("検索条件を選び「記事を表示」クリック")
st.session_state.set_keyword= st.sidebar.selectbox("キーワードを選択", set_keyword_list.keys())
st.session_state.set_domains = st.sidebar.selectbox("ソースを選択", set_domains_list.keys())
st.session_state.days_back = st.sidebar.slider('何日前までの記事を取得しますか', 1, 5, 3)
st.session_state.number_of_part = st.sidebar.slider('表示する記事の数', 1, 10, 5)


# ボタンを押した時に記事取得->タイトル翻訳表示が行われるようにしたい
if st.sidebar.button("記事を表示", type="primary") :
    st.session_state.article_blank = True  # Tureの時のみ、後段のif内が実行される
#with st.spinner("タイトル取得中です"):
#   time.sleep(5) #ここ、実際のロード時間に基づき表示できるようにしたい。。

if st.session_state.article_blank :
    
    date_to = datetime.now().date()
    date_from_param = date_to - timedelta(days=st.session_state.days_back)
    

    # 記事の取得
    data_articles = get_articles(set_keyword_list[st.session_state.set_keyword], set_domains_list[st.session_state.set_domains], date_from_param, date_to) 

    # 表示する記事の数を絞る（記事数の方が少ない場合はすべて表示されるはず）
    part_of_data_articles = data_articles.head(st.session_state.number_of_part)

    # "日本語タイトル"のコラムを新規に作成して追加
    add_japanese_column(part_of_data_articles)

    st.session_state.data_articles = part_of_data_articles

    # URLを取得する際にindexを使いたいので、(index+日本語タイトル)を一つの文字列にしたリストを作る
    st.session_state.index_japanese_title_pair_list = []
    
    for article in part_of_data_articles.iterrows():
        _str = str(article[0]) + "_" + str(article[1]["日時"]) + ":" + str(article[1]["日本語タイトル"])   # 文字列からindexを抽出する際には"_"でsplitするつもり
        st.session_state.index_japanese_title_pair_list.append(_str)
 
    st.session_state.article_blank = None  # 記事を取得、翻訳済みなのでNoneにする
        
# ラジオボタンで記事を選択する

set_article = st.radio(
    "**検索結果**",
    st.session_state.index_japanese_title_pair_list,
    index = None,
)

st.markdown('<span style = "font-size: smaller;">"**選択した記事のURL・要約（要約は30秒ほどかかります)**"</span>', unsafe_allow_html=True)

# ラジオボタンを押したときのみ以下を実行する
if set_article != None :

    #st.write("選択した記事：" + str(set_article.split("_")[1]))   # "_"の後ろ部分の日時：タイトルを抽出

    st.session_state.article_index = int(set_article.split("_")[0])  # "_"の手前部分のindexを抽出

    st.session_state.article_url = st.session_state.data_articles["URL"][st.session_state.article_index]  # URLを取得->スクレイピングに使ってください
    
    st.write("URL:" + str(st.session_state.article_url))
    
    #ラジオボタンで選択した記事の要約を表示----
    REQUEST_URL = st.session_state.article_url  #アクセス先をREQUEST_URLを代入
    res = requests.get(REQUEST_URL) #リクエストしたデータをresに代入
    
    #BBCでのスクレイピング機能
    soup = BeautifulSoup(res.text,"html.parser")
    content = soup.select('#main-content > article')
    lines = []
    for t in content:
        lines.append(t.text)
    article = ' '.join(lines) #辞書型からテキストに変更
    
    #ChatGPTでの翻訳機能
    def run_gpt(content_to_text):
        request_to_gpt = "以下を日本語に翻訳し、翻訳した文章を100文字以内で要約してください。" + content_to_text

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": request_to_gpt},
            ],
        )
    
        output_content = response.choices[0]["message"]["content"].strip()
        return output_content
    
    output_content_text = run_gpt(article)
    st.write("要約:" + output_content_text)
    