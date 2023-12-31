from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *
from botocore.exceptions import ClientError

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
s3=boto3.client('s3')


#if call / then will redirect to that pg

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('CompanyLogin.html')


@app.route("/companyLogin", methods=['GET','POST'])
def companyLogin():
    companyEmail = request.form['companyEmail']
    companyPassword = request.form['companyPassword']
    company_filename_in_s3 = str(companyEmail) + "_file.pdf"
    expiration = 3600
    
    fetch_company_sql = "SELECT * FROM company WHERE companyEmail = %s"
    cursor = db_conn.cursor()

    if companyEmail == "" and companyPassword == "":
        return render_template('CompanyLogin.html', empty_field=True)

    try:
        cursor.execute(fetch_company_sql, (companyEmail))
        companyRecord = cursor.fetchone()

        if not companyRecord:
            return render_template('CompanyLogin.html', no_record=True)

        if companyRecord[8] != "Approved":
            return render_template('CompanyLogin.html', not_Approved=True)

        if companyRecord[7] != companyPassword:
            return render_template('CompanyLogin.html', login_failed=True)
        else:
            try:
                response = s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': custombucket,
                                                            'Key': company_filename_in_s3},
                                                    ExpiresIn=expiration)
            except ClientError as e:
                logging.error(e)

            if response is None:
                return render_template('CompanyPage.html', company = companyRecord, file_exist = False)
            else:
                return render_template('CompanyPage.html', company = companyRecord, file_exist = True, url = response)

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

@app.route("/companyUpload", methods=['POST'])
def companyUpload():
    companyEmail = request.form['companyEmail']
    company_File = request.files['company_File']
    company_filename_in_s3 = str(companyEmail) + "_file.pdf"
    
    fetch_company_sql = "SELECT * FROM company WHERE companyEmail = %s"
    cursor = db_conn.cursor()
    
    try:
        expiration = 3600
        try:
            response = s3.generate_presigned_url('get_object',
                                                Params={'Bucket': custombucket,
                                                        'Key': company_filename_in_s3},
                                                ExpiresIn=expiration)
        except ClientError as e:
            logging.error(e)
        cursor.execute(fetch_company_sql, (companyEmail))
        companyRecord = cursor.fetchone()

        if company_File.filename == "":
            if response is None:
                return render_template('CompanyPage.html', company=companyRecord, no_file_uploaded=True, file_exist = False)
            else:
                return render_template('CompanyPage.html', company=companyRecord, file_exist = True, url = response, no_file_uploaded=True)
        else:
            upload = boto3.resource('s3')
            upload.Bucket(custombucket).put_object(Key=company_filename_in_s3, Body=company_File)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            upload_location = (bucket_location['LocationConstraint'])

            if upload_location is None:
                upload_location = ''
            else:
                upload_location = '-' + upload_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                upload_location,
                custombucket,
                company_filename_in_s3)

            try:
                response = s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': custombucket,
                                                            'Key': company_filename_in_s3},
                                                    ExpiresIn=expiration)
            except ClientError as e:
                logging.error(e)

            if response is None:
                return render_template('CompanyPage.html', company = companyRecord, file_exist = False)
            else:
                return render_template('CompanyPage.html', company = companyRecord, file_exist = True, url = response)
        
    except Exception as e:
        return str(e)

    finally:
        cursor.close()
    
    #return render_template('CompanyPage.html', company=companyRecord)


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
