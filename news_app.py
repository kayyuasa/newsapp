import streamlit as st

# 環境ファイルからAPI KEYを指定するのに使用
import os
from dotenv import load_dotenv

#News APIから記事情報を取得
from newsapi import NewsApiClient
import pandas as pd

#ChatGPTでの翻訳機能
import openai

# .envファイルのパスを指定して読み込む
load_dotenv('.env')

# 環境変数を利用する
NEWS_API_KEY =  os.getenv('NEWS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 追々、ニュースソースと記事を選べるようにリストを作成
set_domains_list = {
    "BBC" : 'bbc.co.uk,bbc.com',
}

#　辞書形式で一旦与えておくが、フリーで入力してもらう方がよいのかも
set_keyword_list = {
    "AI" : "AI"
}

# 状態を保持したい変数を指定
if 'set_domains' not in st.session_state:
    st.session_state.set_domains = "BBC"  # デフォルトをBBCにしておく
    st.session_state.article_blank = True  # Trueの時のみ、記事の取得、タイトルの翻訳を行う

if 'set_keyword' not in st.session_state:
    st.session_state.set_keyword = "AI"  # デフォルトをAIにしておく

if 'set_article' not in st.session_state:
    st.session_state.set_article = ""  # デフォルトを""にしておく



def get_articles(keyword, domains):
    # Init
    newsapi = NewsApiClient(api_key=NEWS_API_KEY)

    all_articles = newsapi.get_everything(q=keyword,
                                        #sources='bbc-news',
                                        domains=domains,
                                        from_param='2023-10-10',
                                        to='2023-11-04',
                                        language='en',
                                        #sort_by='relevancy',
                                        #page=2
                                        )
    # print(all_articles['articles'])


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
def transrate_titl_to_japanese(content_text_to_gpt):
    
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
        output_japanese_title = transrate_titl_to_japanese(data_articles["タイトル"][i])
        # 翻訳されたタイトルをリストに追加
        _list.append(output_japanese_title)

    # "日本語タイトル"を新規に作成してリストを入れる
    data_articles.loc[:, "日本語タイトル"] = _list  # .locを使って、明示的にdata_articlesを直接変更したつもりだが、 SettingWithCopyWarningが消えない
    
    return data_articles



st.title("Newsアプリ") # タイトル

st.session_state.set_keyword= st.selectbox("キーワードを選択してください", set_keyword_list.keys())
st.session_state.set_domains = st.selectbox("ソースを選択してください", set_domains_list.keys())

if st.session_state.article_blank :

    # 記事の取得
    data_articles = get_articles(set_keyword_list[st.session_state.set_keyword], set_domains_list[st.session_state.set_domains]) 

    # st.dataframe(data_articles)

    # お試しとして一部分のみを実行する。
    part_number = 5
    part_of_data_articles = data_articles.head(part_number)

    # "日本語タイトル"のコラムを新規に作成して追加
    add_japanese_column(part_of_data_articles)

    # st.dataframe(part_of_data_articles["日本語タイトル"])

    st.session_state.data_articles = part_of_data_articles

    st.session_state.index_japanese_title_pair_list = []
    for index, value in enumerate(part_of_data_articles["日本語タイトル"]):
        st.session_state.index_japanese_title_pair_list.append([index, value])
    
       
    st.session_state.article_blank = None  # 記事を取得、翻訳済みなのでNoneにする


# st.session_state.set_article = st.radio(
#     "記事のタイトル",
#     index_japanese_title_pair_list,
#     index = None,
# )

# st.write("選択した記事：" + str(st.session_state.set_article))

set_article = st.radio(
    "記事のタイトル",
    st.session_state.index_japanese_title_pair_list,
    index = None,
)
print(set_article)

st.write("選択した記事：" + str(set_article))

# set_articleがstrになっている？　文字列からindexを抽出する必要がありそう
# st.write(str(set_article[0]))

# st.write("選択した記事のURL：" + str(st.session_state.data_articles['URL'][set_article[0]]))


