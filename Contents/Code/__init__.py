NAME = "Haystack TV"
PREFIX = '/video/haystack'
BASE_URL = "https://www.haystack.tv"
YT_URL = "https://www.youtube.com/watch?v="

ICON = 'icon-default.png'

RE_JSON = Regex('window.__INITIAL_STATE__ = (.+?);\n', Regex.DOTALL)

####################################################################################################
def Start():

    ObjectContainer.title1 = NAME
    DirectoryObject.thumb = R(ICON)
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'

####################################################################################################
@handler(PREFIX, NAME, thumb=ICON)
def MainMenu():

    oc = ObjectContainer()
    json = GetData(BASE_URL)
    try: section_list = json['environment']['sitemap']
    except: return ObjectContainer(header="Empty", message="The website for this channel does not return data.")
    
    for item in section_list:

        section_title = json['environment']['sitemap'][item]['sectionTitle']
        if item == '/':
            section_url = BASE_URL
        else:
            section_url = BASE_URL + item
        if 'liveeditor' in section_url:
            continue
        section_description = json['environment']['sitemap'][item]['pageTitle']
        oc.add(DirectoryObject(key=Callback(Videos, title=section_title, url=section_url), title=section_title, summary=section_description))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no sections for this channel." )
    else:
        return oc

####################################################################################################
@route(PREFIX + '/videos')
def Videos(url, title):

    oc = ObjectContainer(title2=title)
    json = GetData(url)

    for item in json['videos']['videoList']:

        stream_url = item['streamUrl']
        date = item['publishedDate']
        # One date value gives errors on some clients but cannot see any error with it
        #Log('The value of date is %s' %date)
        date = Datetime.ParseDate(item['publishedDate'])
        try:
            duration = duration = item['duration'] * 1000
            duration = int(duration)
        except: duration = 0
        try: thumb = item['thumbnail']['downloadUrl']
        except: thumb = item['snapshotHighUrl']

        if 'mediaFiles' in item:
            available_streams = []
            media_list = item['mediaFiles']
            for media_item in media_list:
                media_source = item['mediaFiles'][media_item]['url']
                media_type = item['mediaFiles'][media_item]['type']
                #Log('the value of the media is %s, resolution is %s, and type is %s' %(media_source, media_item, media_type))
                media_quality = GetResolution(media_item, media_type)
                media_info = {'quality' : media_quality, 'type' : media_type, 'media_url': media_source}
                available_streams.append(media_info)
            oc.add(
                CreateVideoClipObject(
                    title = item['title'],
                    url = stream_url,
                    media_data = available_streams,
                    originally_available_at = date,
                    duration = duration,
                    thumb = thumb
                )
            )
        elif '/youtu.be/' in stream_url:
            yt_id = stream_url.split('/')[-1]
            yt_url = YT_URL + yt_id
            oc.add(
                VideoClipObject(
                    title = item['title'],
                    url = stream_url,
                    originally_available_at = date,
                    duration = duration,
                    thumb = Resource.ContentsOfURLWithFallback(url=thumb)
                )
            )
        else:
            continue

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos for this listing." )
    else:
        return oc

####################################################################################################
@route(PREFIX + '/createvideoclipobject', media_data=list, include_container=bool)
def CreateVideoClipObject(media_data, url, title, originally_available_at, duration, thumb, include_container=False, **kwargs):

    media_objects = []
    for media in media_data:
        #Log('the values before creating objects is the media is %s, resolution is %s, and type is %s' %(media['media_url'], media['quality'], media['type']))
        resolution = media['quality']
        if 'mp4' in media['type']:
            media_objects.append(
                MediaObject(
                    parts = [
                        PartObject(key=media['media_url'])
                    ],
                    video_resolution = resolution,
                    container = Container.MP4,
                    video_codec = VideoCodec.H264,
                    audio_channels = 2,
                    audio_codec = AudioCodec.AAC,
                )
            )
        elif 'm3u8' in media['type']:
            media_objects.append(
                MediaObject(
                    parts = [
                        PartObject(key=HTTPLiveStreamURL(media['media_url']))
                    ],
                    video_resolution = resolution,
                    container = 'mpegts',
                    protocol = 'hls'
                )
            )
        else:
            continue

    videoclip_obj = VideoClipObject(
        key = Callback(CreateVideoClipObject, media_data=media_data, url=url, title=title, originally_available_at=originally_available_at, duration=duration, thumb=thumb, include_container=True),
        rating_key = url,
        title = title,
        duration = duration,
        originally_available_at = originally_available_at,
        thumb = Resource.ContentsOfURLWithFallback(url=thumb),
        items = media_objects
    )

    if include_container:
        return ObjectContainer(objects=[videoclip_obj])
    else:
        return videoclip_obj

####################################################################################################
# This function pulls the json data from an HTMl page page_data
@route(PREFIX + '/getdata')
def GetData(url):
    
    try: content = HTTP.Request(url).content
    except: return ObjectContainer(header="Empty", message="The website for this channel does not return data.")
    #Log('the value of content is %s' %content)
    try: page_data = RE_JSON.search(content).group(1)
    except: page_data = ''
    #Log('the value of page_data is %s' %page_data)

    try: json = JSON.ObjectFromString(page_data)
    except: json = None

    return json
####################################################################################################
# This function determines the resolution of media
@route(PREFIX + '/getresolution')
def GetResolution(media_quality, media_type):
    
    #Log('the value of media_quality is %s and media_type is %s' %(media_quality, media_type))
    if '1080' in media_quality:
        resolution = 1080
    elif '720' in media_quality:
        resolution = 720
    elif 'small' in media_quality:
        resolution = 270
    elif 'medium' in media_quality:
        if media_type=='mp4':
            resolution = 406
        else:
            resolution = 360
    elif 'adaptive' in media_quality:
        resolution = 720
    else:
        resolution = 420
    #Log('the value of resolution is %s' %resolution)

    return resolution
