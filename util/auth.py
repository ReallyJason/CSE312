percent_encode = {
    '%21': '!',
    '%40': '@',
    '%23': '#',
    '%24': '$',
    '%25': '%',
    '%5E': '^',
    '%26': '&',
    '%28': '(',
    '%29': ')',
    '%2D': '-',
    '%5F': '_',
    '%3D': '='
}

def pdecode(s):
    decoded=''
    i=0

    while i<len(s):
        if s[i]=='%':
            decoded=decoded+percent_encode[s[i:i+3]]
            i+=3
        else:
            decoded=decoded+s[i]
            i+=1
    return decoded


def extract_credentials(request):
    body=request.body.decode("utf-8")
    username=""
    password=""
    totpCode=""
    totpCode_Found=False

    for keyval in body.split("&"):
        if not keyval:
            continue
        if "=" in keyval:
            key,value=keyval.split("=",1)
        else:
            key,value=keyval,""
        if key=="username":
            username=value
            continue

        key=pdecode(key)
        value=pdecode(value)
        if key=="password":
            password=value
        if key=="totpCode":
            totpCode=value
            totpCode_Found=True

    if totpCode_Found:
        return [username, password, totpCode]
    return [username, password]

def validate_password(password):
    one_lower=one_upper=special_character=one_digit=False

    if len(password) < 8:
        return False
    for char in password:
        if char.islower(): one_lower=True
        if char.isupper(): one_upper=True
        if char.isdigit(): one_digit=True
        if char in percent_encode.values(): special_character=True
        if not char.isalnum() and char not in percent_encode.values(): return False

    return one_lower and one_upper and special_character and one_digit