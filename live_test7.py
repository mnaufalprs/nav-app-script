import subprocess
import mysql.connector
import datetime
import time
import re
import multiprocessing


last_primary_key = None
user_id_satu = None

# Buat koneksi ke database
def create_db_connection():
    # return mysql.connector.connect(
    #     host="34.87.72.140",
    #     user="root",
    #     password="admin123",
    #     database="project_webapp"
    # )
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

# Fungsi untuk memeriksa data baru
def check_for_new_data(cursor):
    global last_primary_key, user_id_satu
    # Ambil data baru dengan id terbesar
    cursor.execute("SELECT MAX(id) FROM input_livetests")
    latest_primary_key = cursor.fetchone()[0]

    # Periksa apakah ada data baru dengan id berbeda dan status_connect=1
    if latest_primary_key != last_primary_key:
        # Ambil status_connect dari data terbaru
        cursor.execute(f"SELECT id, user_id, status_connect FROM input_livetests WHERE id = {latest_primary_key}")
        result = cursor.fetchone()
        latest_status_connect = result[2]
        user_id_satu = result[1]
        print(latest_status_connect) 
        # Periksa apakah status_connect adalah 1
        if latest_status_connect == 1:
            last_primary_key = latest_primary_key
            return True

    return False

# Fungsi untuk mendapatkan data terbaru untuk pengguna tertentu
def get_latest_live_test_data(cursor, user_id):
    cursor.execute(f"SELECT * FROM input_livetests WHERE user_id = {user_id} ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()

# Fungsi pengukuran berkelanjutan untuk pengguna tertentu
def continuous_measurement(user_data):
    user_id = user_data[1]
    conn = create_db_connection()
    cursor = conn.cursor()
    
    while True:
        try:
            latest_live_test_data = get_latest_live_test_data(cursor, user_id)
            if latest_live_test_data:
                id = latest_live_test_data[0]
                user_id = latest_live_test_data[1]
                #print("Pengguna ke : ", user_id)
                server_address = latest_live_test_data[4]
                request_per_second = latest_live_test_data[5]
                connection_count = latest_live_test_data[6]

                waktu_format, id, user_id, avg_time_taken_test, avg_request_loss_test, avg_request_per_second, avg_time_per_request1, avg_time_per_request2, avg_transfer_rate, avg_connection_time = pengukuran(server_address, request_per_second, connection_count, user_id, id)

                upload_pengukuran(cursor, conn, waktu_format, id, user_id, server_address, avg_time_taken_test, avg_request_loss_test, avg_request_per_second, avg_time_per_request1, avg_time_per_request2, avg_transfer_rate, avg_connection_time)
                
                # Periksa apakah status_connect masih 1
                latest_status = get_latest_live_test_data(cursor, user_id)
                if latest_status and latest_status[9] == 0:
                    print(f"Pengukuran berhenti untuk user {user_id} karena status_connect = 0 pada database livetests.")
                    break

            time.sleep(3)
        except mysql.connector.Error as err:
            print("Error koneksi database bermasalah")
            time.sleep(1)
            cursor.close()
            conn.close()
            conn = create_db_connection()
            cursor = conn.cursor()
        except Exception as e:
            print("Unexpected error:", e)
            time.sleep(1)
    
    cursor.close()
    conn.close()

# Fungsi pengukuran
def pengukuran(server_address, request_per_second, connection_count, user_id, id, loop=1):
    total_time_taken_test_list = []
    total_complete_request_list = []
    total_request_per_second_list = []
    total_time_per_request1_list = []
    total_time_per_request2_list = []
    total_transfer_rate_list = []
    total_connection_time_list = []

    waktu_sekarang = datetime.datetime.now()
    waktu_format = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")

    for measurement in range(1, loop + 1):
        command = f"ab -n {connection_count} -c {request_per_second} http://{server_address}/"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()

        time_taken_match = re.search(r"Time taken for tests:([\s\d.]+) seconds", output.decode())
        complete_request_match = re.search(r"Complete requests:([\s\d.]+)", output.decode())
        requests_per_second_match = re.search(r"Requests per second:([\s\d.]+) \[#/sec\] \(me", output.decode())
        time_per_request1_match = re.search(r"Time per request:([\s\d.]+) \[ms\] \(mean\)", output.decode())
        time_per_request2_match = re.search(r"Time per request:\s+([\d.]+) \[ms\] \(mean, acr", output.decode())
        transfer_rate_match = re.search(r"Transfer rate:([\s\d.]+) \[Kbytes/sec\] received", output.decode())
        connection_time_match = re.search(r"Total:\s+\d+\s+(\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+)", output.decode())

        if time_taken_match:
            time_taken = time_taken_match.group(1).strip()
            total_time_taken_test_list.append(float(time_taken))

        if complete_request_match:
            complete_request = complete_request_match.group(1).strip()
            request_loss = (int(connection_count) - int(complete_request)) * 100
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

        time.sleep(3)

    if total_time_taken_test_list:
        try:
            avg_time_taken_test = sum(total_time_taken_test_list) / len(total_time_taken_test_list)
            avg_request_loss_test = sum(total_complete_request_list) / len(total_complete_request_list)
            avg_request_per_second = sum(total_request_per_second_list) / len(total_request_per_second_list)
            avg_time_per_request1 = sum(total_time_per_request1_list) / len(total_time_per_request1_list)
            avg_time_per_request2 = sum(total_time_per_request2_list) / len(total_time_per_request2_list)
            avg_transfer_rate = sum(total_transfer_rate_list) / len(total_transfer_rate_list)
            avg_connection_time = sum(total_connection_time_list) / len(total_connection_time_list)
        except ZeroDivisionError:
            #print("Pengukuran tidak valid: pembagian oleh nol terjadi.")
            # Setel rata-rata menjadi 0
            avg_time_taken_test = 0.0
            avg_request_loss_test = 100.0
            avg_request_per_second = 0.0
            avg_time_per_request1 = 0.0
            avg_time_per_request2 = 0.0
            avg_transfer_rate = 0.0
            avg_connection_time = 0.0

        return waktu_format, id, user_id, avg_time_taken_test, avg_request_loss_test, avg_request_per_second, avg_time_per_request1, avg_time_per_request2, avg_transfer_rate, avg_connection_time
    else:
        avg_time_taken_test = 0
        avg_request_loss_test = 100
        avg_request_per_second = 0
        avg_time_per_request1 = 0
        avg_time_per_request2 = 0
        avg_transfer_rate = 0
        avg_connection_time = 0

        return waktu_format, id, user_id, avg_time_taken_test, avg_request_loss_test, avg_request_per_second, avg_time_per_request1, avg_time_per_request2, avg_transfer_rate, avg_connection_time

# Fungsi untuk mengupload hasil pengukuran ke database
def upload_pengukuran(cursor, conn, waktu_format, id, user_id, server_address, avg_time_taken_test, avg_request_loss_test, avg_request_per_second, avg_time_per_request1, avg_time_per_request2, avg_transfer_rate, avg_connection_time):

    insert_query = "INSERT INTO data_livetests (input_livetest_id, user_id, server_address, time_taken, request_second, time_request, transfer_rate, connection_time, request_loss, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    data = (id, user_id, server_address, avg_time_taken_test, avg_request_per_second, avg_time_per_request2, avg_transfer_rate, avg_connection_time, avg_request_loss_test, waktu_format)
    try:
        cursor.execute(insert_query, data)
        conn.commit()
        print(f"Data berhasil diinputkan ke dalam database untuk user {user_id}")
    except mysql.connector.Error as err:
        print("Error saat akan mengupload ke database untuk user {user_id}")
        time.sleep(1)

# Fungsi utama untuk mengelola pengukuran berkelanjutan
def main():
    global user_id_satu
    while True:
        conn = create_db_connection()
        cursor = conn.cursor()
        if check_for_new_data(cursor):
            #user_id = user_id_satu
            user_data = get_latest_live_test_data(cursor, user_id_satu)
            if user_data:
                user_id = user_data[1]

                measurement_process = multiprocessing.Process(target=continuous_measurement, args=(user_data,))
                measurement_process.start()


        time.sleep(1)
        cursor.close()
        conn.close()

if __name__ == "__main__":
    last_primary_key = None
    user_id_satu = None
    main()
