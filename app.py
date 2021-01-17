from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import re
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
import mysql.connector
import json
import tweepy
import emoji


from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import confusion_matrix

app = Flask(__name__)
app.secret_key="yurikkkeeeeeeeeee"


auth = tweepy.OAuthHandler("tnvQPn1qpptY5ogds26fAVS0D", "bp352iGcls0IRIiQzwLPdjJz6EGXlyFEpbhYyRvlYVuONLMYAw")
auth.set_access_token("736732046584778752-29tucKHNyqnPncXoIXDj5fPEaWXe3Qp", "WrTVoQERvspBDqRqcgl4oXHqXxFPV6b8rO9p0IBqy9u0T")

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database="indecentTweetClassification"
)



def preprocessingtext(text):
    factory = StopWordRemoverFactory()
    stopword = factory.create_stop_word_remover()
    #### MELAKUKAN PROSES STEMMING STOPWORD BAHASA INDONESIA
    satu = stopword.remove(text)
    #### MENGHILANGKAN TEXT TIDAK PENTING SEPERTI HASHTAG DAN MENTION      
    dua = re.sub(r"@[^\s]+"," ",satu)
    dua = re.sub(r"#[^\s]+"," ",dua)
    dua = re.sub(r"\."," ",dua)
    dua = re.sub(r"http[^\s]+"," ",dua)
    dua = re.sub(r"\?"," ",dua)
    dua = re.sub(r","," ",dua)
    dua = re.sub(r"”"," ",dua)
    dua = re.sub(r"co/[^\s]+"," ",dua)
    dua = re.sub(r":'\)"," ",dua)
    dua = re.sub(r":\)","",dua)
    dua = re.sub(r"&"," ",dua)
    dua = re.sub(r'\"([^\"]+)\"',"\g<1>",dua)
    dua = re.sub(r'\([^\)]+\"',"",dua)
    dua = re.sub(r'\((.+)\)',"\g<1>",dua)
    dua = re.sub(r'-'," ",dua)
    dua = re.sub(r':\('," ",dua)
    dua = re.sub(r':'," ",dua)
    dua = re.sub(r'\('," ",dua)
    dua = re.sub(r'\)'," ",dua)
    dua = re.sub(r"'"," ",dua)
    dua = re.sub(r'"'," ",dua)
    dua = re.sub(r';'," ",dua)
    dua = re.sub(r':v'," ",dua)
    dua = re.sub(r'²'," ",dua)
    dua = re.sub(r':"\)'," ",dua)
    dua = re.sub(r'\[\]'," ",dua)
    dua = re.sub(r'“',"",dua)
    dua = re.sub(r'_'," ",dua)
    dua = re.sub(r'—'," ",dua)
    dua = re.sub(r'…'," ",dua)
    dua = re.sub(r'='," ",dua)
    dua = re.sub(r'\/'," ",dua)
    dua = re.sub(r'\[\w+\]'," ",dua)
    dua = re.sub(r'!'," ",dua)
    dua = re.sub(r"'"," ",dua)
    dua = re.sub(r'\s+'," ",dua)
    dua = re.sub(r'^RT',"",dua) 
    dua = re.sub(r'\s+$',"",dua)   
    dua = re.sub(r'^\s+',"",dua)   
    #### MENGUBAH CASE KATA MENJADI LOWERCASE
    tiga = dua.lower()
    tiga = re.sub(r"\\[^\s]+"," ",tiga)
    return tiga

def give_emoji_free_text(text):
    allchars = [str for str in text.decode('utf-8')]
    emoji_list = [c for c in allchars if c in emoji.UNICODE_EMOJI]
    clean_text = ' '.join([str for str in text.decode('utf-8').split() if not any(i in str for i in emoji_list)])
    return clean_text


@app.before_request
def before_request():
    if request.endpoint=="login":
        if 'isLogin' in session:
            return redirect(url_for("dashboard"))
    elif request.endpoint!="login" and "isLogin" not in session:
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.pop("isLogin",None)
    return redirect(url_for("login"))

@app.route("/", methods=["POST","GET"])
def login():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        if len(username)==0 or len(password)==0:
            return render_template("login.html", error="Username atau password tidak boleh kosong...")

        mydb.connect()
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM admin WHERE username=%s",(username,))
        myresult = cursor.fetchone()
        if myresult==None:
            return render_template("login.html", error="Login gagal...")
        else:
            u = myresult[1]
            p = myresult[2]
            if u==username and p==password:
                session["isLogin"]=True
                return redirect(url_for("dashboard"))
            else:
                return render_template("login.html", error="Login gagal...")
    return render_template("login.html")

@app.route("/dashboard", methods=["POST","GET"])
def dashboard():
    if request.method=="POST":
        username = request.form["username"]
        if len(username)==0:
            return render_template("dashboard.html",error="Masukkan username...")
        api = tweepy.API(auth)
       
        try:
            user = api.get_user(id=username)
            hasil = api.user_timeline(id=username, count=50, tweet_mode="extended")
            tweet = []
            for t in hasil:
                if (not t.retweeted) and ('RT @' not in t.full_text):
                    tweet.append(t.full_text)
            preprocessed = [preprocessingtext(give_emoji_free_text(x.encode())) for x in tweet]
            preprocessed = [re.sub(r"\\[^\s]+","",x.encode("unicode-escape").decode("utf-8")) for x in preprocessed]


            cursor = mydb.cursor()
            cursor.execute("SELECT * FROM preprocessing")
            myresult = cursor.fetchall()

            X = []
            y = []

            for l in myresult:
                X.append(l[0])
                y.append(l[1])


            vectorizer = TfidfVectorizer(min_df=0.0, max_df=1.0, sublinear_tf=True, use_idf=True, stop_words='english')


            X_train_tf = vectorizer.fit_transform(X)
            preprocessed_tf = vectorizer.transform(preprocessed)

            model = MultinomialNB()
            model.fit(X_train_tf, y)
            result = model.predict(preprocessed_tf)

            payload = []
            for index,value in enumerate(result):
                payload.append({"text":tweet[index],"klasifikasi":value})
            return  render_template("dashboard.html",data=payload)
        except Exception as e:
            print(e)
            return render_template("dashboard.html",error="Tidak ditemukan user tersebut")
    
            
          
    return render_template("dashboard.html")

@app.route("/dataset", methods=["POST","GET"])
def dataset():
    if request.method == 'POST':
        if 'file' not in request.files or len(request.files["file"].filename)==0:
            return redirect(url_for('dataset'))
        file = request.files['file']
        excel = pd.read_excel(file)

        cursor = mydb.cursor()
        cursor.execute("DELETE FROM dataset")
        mydb.commit()

        sql = "INSERT INTO dataset (text,klasifikasi) VALUES (%s,%s)"

        tupp = []
        counter=-1
        for x in excel["tweet"]:
            counter=counter+1
            tupp.append((x.encode("unicode-escape"),excel["hasil"][counter]))

        
        cursor.executemany(sql,tupp)
        mydb.commit()

        return redirect(url_for("dataset"))
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM dataset")
    myresult = cursor.fetchall()

    arr = []
    count=0
    for x in myresult:
        count=count+1
        arr.append({"no":count,"text":x[0],"klasifikasi":x[1]})
    
    return render_template("dataset.html",data=arr)

@app.route("/preprocessing",methods=["POST","GET"])
def preprocessing():
    if request.method=="POST":
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM dataset")
        myresult = cursor.fetchall()

        payload = []

        for x in myresult:
            hasilpraproses = preprocessingtext(x[0])
            payload.append((hasilpraproses,x[1]))

        cursor = mydb.cursor()
        cursor.execute("DELETE FROM preprocessing")
        mydb.commit()

        sql = "INSERT INTO preprocessing (text,klasifikasi) VALUES (%s,%s)"
        cursor.executemany(sql,payload)
        mydb.commit()

        return redirect(url_for("preprocessing"))
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM preprocessing")
    myresult = cursor.fetchall()
    cursor.execute("SELECT * FROM dataset")
    myresult2 = cursor.fetchall()

    arr = []
    count=0
    for x in myresult:
        count=count+1
        arr.append({"no":count,"previous":myresult2[count-1][0],"after":x[0],"klasifikasi":x[1]})
    
    return render_template("textpreprocessing.html", data=arr)

@app.route("/klasifikasi")
def klasifikasi():
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM preprocessing")
    myresult = cursor.fetchall()

    X = []
    y = []

    for l in myresult:
        X.append(l[0])
        y.append(l[1])

    X_train, X_test, y_train, y_test = train_test_split(X,y, test_size=0.1, train_size=0.9, random_state=45)
    vectorizer = TfidfVectorizer(min_df=0.0, max_df=1.0, sublinear_tf=True, use_idf=True, stop_words='english')

    X_train_tf = vectorizer.fit_transform(X_train)
    X_test_tf = vectorizer.transform(X_test)

    model = MultinomialNB()
    model.fit(X_train_tf, y_train)
    result = model.predict(X_test_tf)

    c=-1
    p = []
    for x in result:
        c=c+1
        p.append({"no":c+1,"text":X_test[c],"klasifikasi":x})
    
    print(confusion_matrix(y_test,result))
    return render_template("klasifikasi.html", data=p)

@app.route("/pengujian")
def pengujian():
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM preprocessing")
    myresult = cursor.fetchall()

    X = []
    y = []

    for l in myresult:
        X.append(l[0])
        y.append(l[1])

    X_train, X_test, y_train, y_test = train_test_split(X,y, test_size=0.1, train_size=0.9, random_state=45)
    vectorizer = TfidfVectorizer(min_df=0.0, max_df=1.0, sublinear_tf=True, use_idf=True, stop_words='english')

    X_train_tf = vectorizer.fit_transform(X_train)
    X_test_tf = vectorizer.transform(X_test)

    model = MultinomialNB()
    model.fit(X_train_tf, y_train)
    result = model.predict(X_test_tf)

    c=-1
    p = []
    for x in result:
        c=c+1
        p.append({"no":c+1,"text":X_test[c],"klasifikasi":x})
    
    matrix = confusion_matrix(y_test,result)
    cmatrix = [{ "kosong": "Actual True", "actualtrue": int(matrix[0][0]), "actualfalse": int(matrix[0][1]) },{ "kosong": "Actual False", "actualtrue": int(matrix[1][0]), "actualfalse": int(matrix[1][1]) }]
    cmatrix_dump = json.dumps(cmatrix)
    return render_template("pengujian.html", cmatrix=cmatrix_dump)

if __name__=='__main__':
    app.run(debug=True)