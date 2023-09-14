from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'company'


#if call / then will redirect to that pg

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('CompanyLogin.html')


@app.route("/companyLogin", methods=['GET', 'POST'])
def companyLogin():
    companyEmail = request.form['companyEmail']
    companyPassword = request.form['companyPassword']
    company_filename_in_s3 = str(companyEmail) + "_file.pdf"
    expiration = 3600
    
    fetch_company_sql = "SELECT * FROM company WHERE companyEmail = %s"
    cursor = db_conn.cursor()
    cursor.close()
    if companyEmail == "" and companyPassword == "":
        return render_template('CompanyLogin.html', empty_field=True)

    try:
        cursor.execute(fetch_company_sql, (companyEmail))
        companyRecord = cursor.fetchone()

        if companyRecord == None:
            return render_template('CompanyLogin.html', no_record=True)

        if companyRecord[8] == "Pending Approval" or companyRecords[8] == "Rejected":
            return render_template('CompanyLogin.html', not_Approved=True)

        if companyRecord[7] != companyPassword:
            return render_template('CompanyLogin.html', login_failed=True)
        else:
            try:
                response = s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': custombucket,
                                                            'Key': object_key},
                                                    ExpiresIn=expiration)
            except ClientError as e:
                logging.error(e)

            if response == None:
                return render_template('CompanyPage.html', company = companyRecord)
            else:
                return render_template('CompanyPage.html', company = companyRecord, url = url)     
    except Exception as e:
        return str(e)

    finally:
        cursor.close()

@app.route("/companyUpload", methods=['POST'])
def companyUpload():
    companyFile = request.files['companyFile']
    companyEmail = request.args.get('companyEmail')

    if companyFile.filename == "":
        return render_template('CompanyPage.html', no_file=True)
    
    fetch_company_sql = "SELECT * FROM company WHERE companyEmail = %s"
    cursor = db_conn.cursor()
    company_filename_in_s3 = str(companyEmail) + "_file.pdf"
    s3 = boto3.resource('s3')

    try:
        cursor.execute(fetch_company_sql, (companyEmail))
        companyRecord = cursor.fetchone()
        s3.Bucket(custombucket).put_object(Key=company_filename_in_s3, Body=companyFile)
        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
        s3_location = (bucket_location['LocationConstraint'])

        if s3_location is None:
            s3_location = ''
        else:
            s3_location = '-' + s3_location

        object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
            s3_location,
            custombucket,
            company_filename_in_s3)

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
    
    return render_template('CompanyPage.html', company = companyRecord)


@app.route("/companyReg", methods=['POST'])
def companyReg():
    companyName = request.form['companyName']
    companyEmail = request.form['companyEmail']
    companyContact = request.form['companyContact']
    companyAddress = request.form['companyAddress']
    typeOfBusiness = request.form['typeOfBusiness']
    numOfEmployee = request.form['numOfEmployee']
    overview = request.form['overview']
    companyPassword = request.form['companyPassword']
    status = "Pending Approval"

    insert_sql = "INSERT INTO company VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:

        cursor.execute(insert_sql, (companyName, companyEmail, companyContact, companyAddress, typeOfBusiness, numOfEmployee, overview, companyPassword, status))
        db_conn.commit()
        

    except Exception as e:
        return str(e) 
        

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('CompanyLogin.html')


@app.route("/adminLogin", methods=['GET', 'POST'])
def adminLogin():
    adminEmail = request.form['adminEmail']
    adminPassword = request.form['adminPassword']
    status = "Pending Approval"


    
    fetch_admin_sql = "SELECT * FROM admin WHERE adminEmail = %s"
    fetch_company_sql = "SELECT * FROM company WHERE status = %s"
    cursor = db_conn.cursor()

    if adminEmail == "" and adminPassword == "":
        return render_template('AdminLogin.html', empty_field=True)

    try:
        cursor.execute(fetch_admin_sql, (adminEmail))
        records = cursor.fetchall()

        cursor.execute(fetch_company_sql, (status))
        companyRecords = cursor.fetchall()

        if records and records[0][2] != adminPassword:
            return render_template('AdminLogin.html', login_failed=True)
        else:
            return render_template('AdminPage.html', admin=records, company=companyRecords)

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
