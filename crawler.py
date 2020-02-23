import shutil, os, collections, re, base64, time
import numpy as np

from selenium import webdriver
from PIL import Image
from slugify import slugify
import cfg

DEFAULT_SIZE = 12000
DEFAULT_HOST = 'https://artsandculture.google.com/asset/'

def parse(url, size, raise_errors, blobs_folder):
    try:
        cleanup(blobs_folder)
        if not DEFAULT_HOST in url:
            raise ValueError

        # print("> Opening website")
        ret, file_name = generate_image(url, size, raise_errors, blobs_folder)
        cleanup(blobs_folder)
        return (ret, file_name)
    except Exception as e:
        # print("FAILED")
        if raise_errors:
            raise e
        # print(e)

def generate_image(url, size, raise_errors, blobs_folder, delay=5):
    mobile_emulation = {
        "deviceMetrics": {"width": size, "height": size, "pixelRatio": 1.0},
        "userAgent": "Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Mobile Safari/535.19"}
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument('--headless')
    #chrome_options.add_argument('--disable-gpu')
    browser = webdriver.Chrome("./chromedriver", options=chrome_options)
    browser.set_window_position(-5000, 0)
    browser.get(url)
    time.sleep(delay)
    blobs = browser.find_elements_by_tag_name('img')
    # print("> Downloading partial images..")
    os.mkdir(blobs_folder)

    title = url.split("/")[-1]
    columns = []
    rows = []
    pil_images = []
    i = 0

    for blob in blobs:
        if i > 2:
            # Get number of rows and columns
            style = blob.get_attribute('style')
            style_end_index = style.find(');')
            # -4 removes "z" translation
            style = style[:style_end_index - 4]
            style = style.replace('transform: translate3d(', '')
            positions = list(map(int, re.findall(r'\d+', style)))

            if len(positions) < 2:
                # The positions are not available for this image - skip
                continue

            columns.append(positions[0])
            rows.append(positions[1])

            # Save blob to file
            image = (get_file_content_chrome(browser, blob.get_attribute('src')))
            filename = blobs_folder + '/{0}.jpg'.format(i)

            with open(filename, 'wb') as f:
                f.write(image)

            # Create PIL objects list
            try:
                pil_images.append(Image.open(blobs_folder + '/{0}.jpg'.format(i)))
            except Exception as e:
                # print("Exception raised")
                cleanup(blobs_folder)
                if raise_errors:
                    raise e
                # print(str(e))
                # print('Trying again...')
                generate_image(url, size, raise_errors, blobs_folder, delay+10)

        i += 1

    # print("> Downloaded {0} partial images".format(len(blobs)))
    columns = (len(collections.Counter(columns).keys()))
    rows = (len(collections.Counter(rows).keys()))

    inverted_pil_images = []

    # by default images are crawled in vertical direction
    # we re-arrange list to create horizontally sorted list
    for j in range(0, rows):
        for i in range(0, columns):
            inverted_pil_images.append(pil_images[(i * rows) + j])

    grid = pil_grid(inverted_pil_images, blobs_folder, raise_errors, columns)
    grid.save(cfg.ASSET_FOLDER + title + '.jpg')

    browser.close()

    return (True, title + '.jpg')

def get_file_content_chrome(driver, uri):
    """
    Saves blob to base64.
    """
    result = driver.execute_async_script("""
    var uri = arguments[0];
    var callback = arguments[1];
    var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),t=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):t%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),new TextDecoder("ascii").decode(a)};
    var xhr = new XMLHttpRequest();
    xhr.responseType = 'arraybuffer';
    xhr.onload = function(){ callback(toBase64(xhr.response)) };
    xhr.onerror = function(){ callback(xhr.status) };
    xhr.open('GET', uri);
    xhr.send();
    """, uri)
    if type(result) == int:
        raise Exception("Request failed with status %s" % result)
    return base64.b64decode(result)


def pil_grid(images, blobs_folder, raise_errors, max_horiz=np.iinfo(int).max):
    """
    Generates one image out of many blobs.
    """
    n_images = len(images)
    n_horiz = min(n_images, max_horiz)
    try:
        h_sizes, v_sizes = [0] * n_horiz, [0] * (n_images // n_horiz)
    except ZeroDivisionError as e:
        cleanup(blobs_folder)

        if raise_errors:
            raise e

    for i, im in enumerate(images):
        h, v = i % n_horiz, i // n_horiz
        h_sizes[h] = max(h_sizes[h], im.size[0])
        v_sizes[v] = max(v_sizes[v], im.size[1])
    h_sizes, v_sizes = np.cumsum([0] + h_sizes), np.cumsum([0] + v_sizes)

    im_grid = Image.new('RGB', (h_sizes[-1], v_sizes[-1]), color='white')
    for i, im in enumerate(images):
        im_grid.paste(im, (h_sizes[i % n_horiz], v_sizes[i // n_horiz]))

    im_grid = np.array(im_grid)

    # print(im_grid.shape)
    v_cut = im_grid.shape[0]
    h_cut = im_grid.shape[1]

    for h in range(im_grid.shape[0]-1, -1, -1):
        if np.sum(im_grid[h, :]):
            v_cut = h
            break

    for w in range(im_grid.shape[1]-1, -1, -1):
        if np.sum(im_grid[:, w]):
            h_cut = w
            break

    im_grid = im_grid[:v_cut, :h_cut]
    im_grid = Image.fromarray(im_grid)

    return im_grid


def cleanup(blobs_folder):
    try:
        shutil.rmtree(blobs_folder + '/')
    except Exception:
        pass
    if not os.path.exists(cfg.ASSET_FOLDER):
        os.makedirs(cfg.ASSET_FOLDER)

