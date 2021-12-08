import imaplib, email
  
# Function to get email content part i.e its body part
def get_body(msg):
    if msg.is_multipart():
        return get_body(msg.get_payload(0))
    else:
        return msg.get_payload(None, True)
  
# Function to search for a key value pair 
def search(key, value, con): 
    result, data = con.search(None, key, '"{}"'.format(value))
    return data
  
# Function to get the list of emails under this label
def get_emails(con, result_bytes):
    msgs = [] # all the email data are pushed inside an array
    for num in result_bytes[0].split():
        typ, data = con.fetch(num, '(RFC822)')
        msgs.append(data)
  
    return msgs

# Return last message with specific subject from gmail, return ('-1', -1) for error
def recv_from_imap(recv_addr, recv_pass, send_addr, imap_server, subject='Sending Test'):
    # this is done to make SSL connnection with Imap Server
    con = imaplib.IMAP4_SSL(imap_server) 
    con.login(recv_addr, recv_pass) 
    
    # calling function to check for email under this label
    con.select('Inbox') 
    
    # Fetch last test message
    msgs = get_emails(con, search('Subject', subject, con))
    if not msgs: return '-1', -1  # Error
    msg = msgs[-1]

    # Parse message
    msg = email.message_from_bytes(msg[0][1])
    content = get_body(msg).decode()

    # Get content
    # return msg['Received'], content
    return content, len(content)