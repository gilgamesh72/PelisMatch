from pelismatch import create_app

app = create_app()
# =============== EJECUCIÓN DEL SERVIDOR ===============
if __name__ == '__main__':
    app.run(debug=True)
