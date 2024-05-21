import subprocess
import re
import mysql.connector
import datetime
import time
import threading


last_primary_key = None
# Variabel global untuk melacak apakah ini pertama kali program dijalankan
is_first_run = True
id_user = None

# Buat koneksi ke database
def create_db_connection():
    while True:
        try:
            conn = mysql.connector.connect(
                host="192.168.100.208",
                user="admin",
                password="Admin123",
                database="project_webapp"
            )
            if conn.is_connected():
                #print("Koneksi ke database berhasil.")
                return conn
        except mysql.connector.Error as err:
            print("Error saat mencoba menghubungkan ke database")
            print("Mencoba kembali dalam 5 detik...")
            time.sleep(3)

def check_for_new_data(cursor, conn):
    global last_primary_key, id_user

    # Periksa apakah koneksi terbuka, jika tidak, buka koneksi
    #if not conn.is_connected():
    #    conn.reconnect()

    # Ambil primary key terbaru
    cursor.execute("SELECT MAX(id) FROM input_wbtests")
    latest_primary_key = cursor.fetchone()[0]

    if latest_primary_key != last_primary_key:
        cursor.execute(f"SELECT id, user_id, server_address FROM input_wbtests WHERE id = {latest_primary_key}")
        result = cursor.fetchone()
        id_user = result[1]
        last_primary_key = latest_primary_key
        return True

    return False

def get_latest_data(cursor, id_user):
    query = f"SELECT * FROM input_wbtests WHERE user_id = {id_user} ORDER BY id DESC LIMIT 1"
    cursor.execute(query)
    row = cursor.fetchone()
    return row

def pengukuran(server_address, request_per_second, connection_count, loop=5):
    total_time_taken_test_list = []
    total_complete_request_list = []
    total_request_per_second_list = []
    total_time_per_request1_list = []
    total_time_per_request2_list = []
    total_transfer_rate_list = []
    total_connection_time_list = []

    waktu_sekarang = datetime.datetime.now()
    waktu_format = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Waktu Pengukuran: {waktu_format} - Alamat Server: {server_address}")

    for measurement in range(1, loop + 1):
        # Menjalankan Apache Bench dengan subproses
        command = f"ab -n {connection_count} -c {request_per_second} http://{server_address}/"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        # Mengambil nilai yang diinginkan dari output menggunakan regular expressions
        time_taken_match = re.search(r"Time taken for tests:([\s\d.]+) seconds", output.decode())
        complete_request_match = re.search(r"Complete requests:([\s\d.]+)", output.decode())
        requests_per_second_match = re.search(r"Requests per second:([\s\d.]+) \[#/sec\]", output.decode())
        time_per_request1_match = re.search(r"Time per request:([\s\d.]+) \[ms\]", output.decode())
        time_per_request2_match = re.search(r"Time per request:\s+([\d.]+) \[ms\]", output.decode())
        transfer_rate_match = re.search(r"Transfer rate:([\s\d.]+) \[Kbytes/sec\]", output.decode())
        connection_time_match = re.search(r"Total:\s+\d+\s+(\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+)", output.decode())

        if time_taken_match:
            time_taken = time_taken_match.group(1).strip()
            total_time_taken_test_list.append(float(time_taken))

        if complete_request_match:
            complete_request = complete_request_match.group(1).strip()
            request_loss = ((int(connection_count) - int(complete_request)) * 100) / int(connection_count)
            total_complete_request_list.append(request_loss)

        if requests_per_second_match:
            requests_per_second = requests_per_second_match.group(1).strip()
            total_request_per_second_list.append(float(requests_per_second))

        if time_per_request1_match:
            time_per_request1 = time_per_request1_match.group(1).strip()
            total_time_per_request1_list.append(float(time_per_request1))

        if time_per_request2_match:
            time_per_request2 = time_per_request2_match.group(1).strip()
            total_time_per_request2_list.append(float(time_per_request2))

        if transfer_rate_match:
            transfer_rate = transfer_rate_match.group(1).strip()
            total_transfer_rate_list.append(float(transfer_rate))

        if connection_time_match:
            connection_time_mean = connection_time_match.group(1).strip()
            total_connection_time_list.append(float(connection_time_mean))

        time.sleep(2)

    # Periksa apakah semua list hasil pengukuran tidak kosong
    if (
        not total_time_taken_test_list
        or not total_complete_request_list
        or not total_request_per_second_list
        or not total_time_per_request1_list
        or not total_time_per_request2_list
        or not total_transfer_rate_list
        or not total_connection_time_list
    ):
        print("Pengukuran tidak valid: list hasil pengukuran kosong.")
        # Setel rata-rata menjadi 0
        avg_time_taken_test = 0.0
        avg_request_loss_test = 100.0
        avg_request_per_second = 0.0
        avg_time_per_request1 = 0.0
        avg_time_per_request2 = 0.0
        avg_transfer_rate = 0.0
        avg_connection_time = 0.0
    else:
        # Perhitungan rata-rata
        try:
            avg_time_taken_test = sum(total_time_taken_test_list) / len(total_time_taken_test_list)
            avg_request_loss_test = sum(total_complete_request_list) / len(total_complete_request_list)
            avg_request_per_second = sum(total_request_per_second_list) / len(total_request_per_second_list)
            avg_time_per_request1 = sum(total_time_per_request1_list) / len(total_time_per_request1_list)
            avg_time_per_request2 = sum(total_time_per_request2_list) / len(total_time_per_request2_list)
            avg_transfer_rate = sum(total_transfer_rate_list) / len(total_transfer_rate_list)
            avg_connection_time = sum(total_connection_time_list) / len(total_connection_time_list)
        except ZeroDivisionError:
            print("Pengukuran tidak valid: pembagian oleh nol terjadi.")
            # Setel rata-rata menjadi 0
            avg_time_taken_test = 0.0
            avg_request_loss_test = 100.0
            avg_request_per_second = 0.0
            avg_time_per_request1 = 0.0
            avg_time_per_request2 = 0.0
            avg_transfer_rate = 0.0
            avg_connection_time = 0.0

    return waktu_format, avg_time_taken_test, avg_request_loss_test, avg_request_per_second, avg_time_per_request1, avg_time_per_request2, avg_transfer_rate, avg_connection_time


def upload_pengukuran(cursor, conn, waktu_format, id, user_id, server_address, avg_time_taken_test, avg_request_loss_test, avg_request_per_second, avg_time_per_request1, avg_time_per_request2, avg_transfer_rate, avg_connection_time, test_id):
    #print('')
    #print("Time taken for tests : ", round(avg_time_taken_test, 2), "seconds")
    #print("Request Loss         : ", round(avg_request_loss_test, 2), "%")
    #print("Requests per second  : ", round(avg_request_per_second, 2), "#/sec")
    #print("Time per request     : ", round(avg_time_per_request1, 2), "ms")
    #print("Time per request     : ", round(avg_time_per_request2, 2), "ms")
    #print("Transfer rate        : ", round(avg_transfer_rate, 2), "Kbytes/sec")
    #print("Connection time      : ", round(avg_connection_time, 2), "ms")

    # melakukan insert data ke database
    insert_query = "INSERT INTO data_wbtests (input_wbtest_id , user_id, server_address, time_taken, request_second, time_request, transfer_rate, connection_time, request_loss, input_test_id, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    data = (
        id,
        user_id,
        server_address,
        avg_time_taken_test,
        avg_request_per_second,
        avg_time_per_request2,
        avg_transfer_rate,
        avg_connection_time,
        avg_request_loss_test,
        test_id,
        waktu_format,
    )
    try:
        cursor.execute(insert_query, data)
        conn.commit()
        print(f"Data berhasil diinputkan ke dalam database untuk user {user_id}")
    except mysql.connector.Error as err:
        #print("Error:", err)
        print(f"Data tidak berhasil diinputkan ke dalam database untuk user {user_id} karena koneksi kedatabase terputus/error")
        time.sleep(1)

def handle_user_input(user_data):
    conn = create_db_connection()
    cursor = conn.cursor()

    id = user_data[0]
    user_id = user_data[3]
    server_address = user_data[4]
    request_per_second = user_data[5]
    connection_count = user_data[6]
    test_id = user_data[9]

    # Lakukan pengukuran
    result = pengukuran(server_address, request_per_second, connection_count)
    if result:
        waktu_format, avg_time_taken_test, avg_request_loss_test, avg_request_per_second, avg_time_per_request1, avg_time_per_request2, avg_transfer_rate, avg_connection_time = result

        # Atur nilai rata-rata menjadi 0 jika tidak valid
        avg_time_taken_test = avg_time_taken_test if avg_time_taken_test is not None else 0.0
        avg_request_loss_test = avg_request_loss_test if avg_request_loss_test is not None else 100.0
        avg_request_per_second = avg_request_per_second if avg_request_per_second is not None else 0.0
        avg_time_per_request1 = avg_time_per_request1 if avg_time_per_request1 is not None else 0.0
        avg_time_per_request2 = avg_time_per_request2 if avg_time_per_request2 is not None else 0.0
        avg_transfer_rate = avg_transfer_rate if avg_transfer_rate is not None else 0.0
        avg_connection_time = avg_connection_time if avg_connection_time is not None else 0.0

        # Cek apakah ini pertama kali program dijalankan
        global is_first_run
        if is_first_run:
            # Jika ini pertama kali program dijalankan, tandai sebagai selesai dan jangan unggah data
            is_first_run = False
            print(f"Pengukuran pertama kali selesai untuk pengguna: {user_id}. Data tidak diunggah ke database.")
        else:
            # Unggah data ke database
            upload_pengukuran(
                cursor,
                conn,
                waktu_format,
                id,
                user_id,
                server_address,
                avg_time_taken_test,
                avg_request_loss_test,
                avg_request_per_second,
                avg_time_per_request1,
                avg_time_per_request2,
                avg_transfer_rate,
                avg_connection_time,
                test_id,
            )
            #print(f"Data berhasil diinputkan ke dalam database untuk pengguna: {user_id}")

    cursor.close()
    conn.close()

def main():
    global is_first_run, id_user
    while True:
        conn = create_db_connection()
        cursor = conn.cursor()
        # Periksa data baru
        if check_for_new_data(cursor, conn):
            latest_data = get_latest_data(cursor, id_user)
            if not latest_data:
                print("Tidak ada data yang tersedia di database.")
                return

            # Buat thread terpisah untuk setiap pengukuran pengguna
            user_thread = threading.Thread(target=handle_user_input, args=(latest_data,))
            user_thread.start()

        # Tunggu sebelum memeriksa lagi (misalnya, setiap 10 detik)
        time.sleep(1)
        cursor.close()
        conn.close()

    # Setelah iterasi pertama selesai, atur `is_first_run` menjadi `False`
    is_first_run = False

if __name__ == "__main__":
    last_primary_key = None
    id_user = None
    main()
