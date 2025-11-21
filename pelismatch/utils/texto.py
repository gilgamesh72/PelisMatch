def normalizar_texto(texto):
    """
    Limpia y normaliza el texto para la comparación difusa.
    """
    texto = texto.lower()
    # Mantenemos tildes y eñes, quitamos otros caracteres no alfanuméricos
    texto = ''.join(c for c in texto if c.isalnum() or c == ' ' or c in 'áéíóúüñ')
    return texto.strip()
