from flask import *
from dotenv import get_key
import mysql.connector
from mysql.connector import pooling
import boto3
from urllib import parse
import time

mysql_user = get_key(".env", "user")
mysql_password = get_key(".env", "password")
aws_access_key = get_key(".env", "aws_access_key")
aws_secret_key = get_key(".env", "aws_secret_key")
s3_bucket_name = get_key(".env", "s3_bucket_name")

s3 = boto3.client('s3', aws_access_key_id=aws_access_key,
                  aws_secret_access_key=aws_secret_key)

app = Flask(
    __name__,
    static_folder="public",
    static_url_path="/"
)

con = mysql.connector.connect(
    host="database-bulletin.cajifi5ilsp4.us-west-2.rds.amazonaws.com",
    user=mysql_user,
    password=mysql_password,
)

cursor = con.cursor()

cursor.execute("DROP database IF EXISTS bulletin;")
cursor.execute("CREATE database bulletin;")
cursor.execute("USE bulletin;")
cursor.execute(
    "CREATE table board (id BIGINT PRIMARY KEY NOT NULL auto_increment,message text,url text);")
cursor.close()
con.close()

conPool = pooling.MySQLConnectionPool(
    user=mysql_user, password=mysql_password, host="database-bulletin.cajifi5ilsp4.us-west-2.rds.amazonaws.com",
    database="bulletin", pool_name="bullentinConPool", pool_size=10)


def error(result, message):
    result["error"] = True
    result["message"] = message
    return result


def createMessage(message, url):
    con = conPool.get_connection()
    cursor = con.cursor()
    cursor.execute(
        "INSERT INTO board (message, url) VALUES (%s, %s)", (message, url))
    con.commit()
    cursor.close()
    con.close()


def readMessage():
    con = conPool.get_connection()
    cursor = con.cursor()
    cursor.execute("SELECT message, url from board ORDER BY id DESC")
    data = cursor.fetchall()
    cursor.close()
    con.close()
    return data


def viewMessage(data):
    result = {}
    result["data"] = []
    for d in data:
        item = {}
        item["message"] = d[0]
        item["url"] = d[1]
        result["data"].append(item)
    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/message", methods=["GET"])
def get():
    data = readMessage()
    result = viewMessage(data)
    return result, 200


@app.route("/api/message", methods=["POST"])
def create():
    result = {}
    try:
        message = request.form["message"]
        file = request.files['file']
        if not message and not file:
            return error(result, "留言失敗：欄位皆為必填"), 400

        filename = time.strftime(
            "%Y%m%d%I%M%S", time.localtime()) + "_" + file.filename

        s3.upload_fileobj(file, s3_bucket_name, filename)

        url = "https://d2qd0ay2cni770.cloudfront.net/" + \
            parse.quote(filename)

        createMessage(message, url)
        result["ok"] = True
        return result, 200

    except Exception as e:
        return error(result, e.__class__.__name__+": "+str(e)), 500


app.run(host="0.0.0.0", port=2052)
