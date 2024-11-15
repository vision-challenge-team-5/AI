from solar_panels import create_app

app = create_app()

# 외부 접속 허용을 위해 '0.0.0.0' 설정, 포트도 원하는 포트로 변경 가능
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
