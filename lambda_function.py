import json
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
#from botocore.vendored import requests
import datetime
from zoneinfo import ZoneInfo
#from bs4 import BeautifulSoup
from facebook import GraphAPI
import certifi
from markdownify import markdownify
import boto3

with open("credentials.json") as f:
        credentials = json.load(f)
MAINTAINER_EMAIL = os.environ.get('MAINTAINER_EMAIL')

# def html_to_text(html):
#     soup = BeautifulSoup(html , "html.parser")
#     text = ''
#     link_load = ""#holds the link for one iteration so that it will appear after label text
#     for e in soup.descendants:
#         if isinstance(e, str):
#             text += e + link_load #tutorial this is from had e.strip(). I don't know why. 
#             link_load = ""
#         elif e.name == 'br': 
#             text += '\n'
#         elif e.name == 'p':
#             text +='\n\n'
#         elif e.name == "a":
#             link_load= " (" + e.get("href") + ") "
#     return text.lstrip('\n')

# SEND EMAIL FUNCTION from https://ivhani.medium.com/sending-an-email-with-aws-lamda-function-python-c4533aabf4af
def send_email(event, recipient):
    gmail_user = 'lwxposter@gmail.com'
    gmail_app_password = os.environ.get('GMAIL_PASS')
    sent_from = gmail_user
    sent_to = recipient
    sent_subject = event["title"]
    sent_body = format_HTML_message(event)
    
    message = MIMEMultipart("alternative")
    message["Subject"] = sent_subject
    message["From"] = gmail_user
    message["To"] = sent_to
    
    html = format_HTML_message(event)
    text = markdownify(html)
    
    
    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    
    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_app_password)
        #starttls
        server.sendmail(sent_from, sent_to, message.as_string())
        server.close()
    except Exception as exception:
        print("Error: %s!\n\n" % exception)

def post_to_fb(event, recipients):
    #https://developers.facebook.com/tools/explorer to get a new one.
    graph = GraphAPI(access_token=credentials['fb_access_token'])

    message = markdownify(format_HTML_message(event))
    
    link = event['pageUrl']
    groups = recipients
 
    for group in groups:
        graph.put_object(group,'feed', message=message,link=link, formatting = "MARKDOWN")
        #print(graph.get_connections(group, 'feed'))

def post_to_discord(event, webhook_url): 
    post_text = markdownify(format_HTML_message(event)) 
    return requests.post(webhook_url, data=json.dumps({ "content": post_text}), headers={ 'Content-Type': 'application/json',}) 


def readable_time(timestamp):
    if not timestamp:
        return None
    timestamp = timestamp.replace("Z", "+00:00")#necessary for fromisoformat
    try:
        d = datetime.datetime.fromisoformat(timestamp)
    except ValueError:
        send_email("timestamp parsing failure", timestamp, MAINTAINER_EMAIL)
        return "" 
    d = d.astimezone(ZoneInfo('America/Los_Angeles'))
    #Thursday, Feb 1 at 12:00 pm PST
    return(f"{d:%A, %b %-d at %-I:%M %p %Z}")

def format_HTML_message(event):
    #TODO: robust handling of empty fields
    title = f"<h2>{event['title']}</h2>"

    time = readable_time(event['startTime'])
    location = event['location']
    contact = f"Contact info: {event['contactInfo']}" if event['contactInfo'] else None
    groups = f"Event types: {', '.join(event['types'])}" if event['types'] else None

    meta_list = [time, location, contact, groups]
    meta_list = [i for i in meta_list if i]
    event_details = f"<p><i>{'<br>'.join(meta_list)}</i></p>"

    original_post_link = f'''<p><i><a href= "{event['pageUrl']}">Crossposted from LessWrong.com</a> by a <a href = "https://github.com/LTGong/LWxposter">friendly bot</a>.<i></p>'''
    body = title + event_details + event["htmlBody"] + original_post_link 
    
    return body 

def query_one_from_server():
    query = """{
      posts(input: {
        terms: {
          view: "upcomingEvents"
          limit: 1
          meta: null  # this seems to get both meta and non-meta posts



        }
      }) {
        results {
          title
          types
          userId
          htmlBody
          pageUrl
          location
          contactInfo
          startTime
        }
      }
}
    """

    url = 'https://www.lesswrong.com/graphql'
    r = requests.post(url, json={'query': query}, headers = {'User-Agent': "'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36'"})
    print(r)
    d = json.loads(r.text)
    return d["data"]["posts"]["results"]

def query_server_timed():
  now = datetime.datetime.now()
  a_week_ago = now - datetime.timedelta(hours=1)
  week_ago_iso = a_week_ago.isoformat()
  query = """{
    posts(input: {
      terms: {
        view: "upcomingEvents"
        after: """ +f'"{week_ago_iso}"'+ """
        
        meta: null  # this seems to get both meta and non-meta posts



      }
    }) {
      results {
        title
        types
        userId
        htmlBody
        pageUrl
      }
    }
  }
  """
  #TODO dry below
  url = 'https://www.lesswrong.com/graphql'
  r = requests.post(url, json={'query': query}, headers = {'User-Agent': "'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36'"})
  print(r)
  d = json.loads(r.text)
  return d["data"]["posts"]["results"]

def get_as_list(query, dest):
    res = dest.get(query)
    if type(res) == str: #catches case where forgot square brackets on single value
        res = [res]
    elif type(res) != list:
        raise TypeError("Unexpected type in JSON object (expected list or string)")
    return res

def dispatch(result, dests):
    #TODO more robust to empty fields in objects
    

    for dest in dests:
        #default state
        location_match = False
        type_match = False

        for target_location in dest['locations']:
            #`"" in "x"` is True, making it a catchall
            if target_location in result["location"] or target_location in result["htmlBody"]:
                location_match = True
        if set(dest["types"]).intersection(result["types"]):
            type_match = True
        if location_match and type_match:
            for email_address in get_as_list("email", dest):
                send_email(result, email_address)
            for fb_address in get_as_list("fb", dest):
                print(fb_address)
                #post_to_fb(result, fb_address)
            for discord_address in get_as_list("discord", dest):
                post_to_discord(result,discord_address)


def read_destinations():
    s3 = boto3.client('s3')
    data = s3.get_object(Bucket='lwx-bucket', Key='destinations.json')
    destinations_json = data['Body'].read().decode("utf8")
    return json.loads(destinations_json)

def handler(event, context): #lambda_handler
    print(event)
    if event['detail-type'] == 'Scheduled Event':  
        results = query_server_timed()      
        results = query_one_from_server()#for testing
    else:
        results = query_one_from_server()
        results += query_one_from_server()#for testing
    
    destination_object = read_destinations()
    print(destination_object)
    for result in results:
        dispatch(result, destination_object)

    return {
        'statusCode': 200,
        'body': json.dumps('Finished A-OK')
    }

if __name__ == "__main__":
    handler({'detail-type':"foo"},"bar")