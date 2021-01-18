import os
import sys

from flask import Flask, redirect, render_template, request

from google.cloud import firestore
from google.cloud import storage
from google.cloud import vision

from helpers import is_valid, get_all_images


app = Flask(__name__)


@app.route('/')
def homepage():
    # Return the homepage
    return render_template('intropage.html')

@app.route('/home')
def intropage():
    # Return the intropage
    return render_template('intropage.html')

@app.route('/image_upload')
def image_upload():
    # Return the homepage
    return render_template('image_upload.html')

@app.route('/tag_photo', methods=['GET', 'POST'])
def tag_photo():
    # If the user inputs an image's link
    if request.form["image-link"]:
        image_public_url = request.form["image-link"]
        client = vision.ImageAnnotatorClient()
        image = vision.types.Image()
        image.source.image_uri = image_public_url

        response = client.label_detection(image=image)

        labels = response.label_annotations

        # Redirect to the scanned image page.
        return render_template('image_scan.html', labels=labels, image_public_url=image_public_url)

    # If a user uploads an image
    else:
        # Create a Cloud Storage client.
        storage_client = storage.Client()

        # Get the Cloud Storage bucket that the file will be uploaded to.
        bucket = storage_client.get_bucket(os.environ.get('CLOUD_STORAGE_BUCKET'))

        # Create a new blob and upload the file's content to Cloud Storage.
        photo = request.files['file']
        blob = bucket.blob(photo.filename)
        blob.upload_from_string(
                photo.read(), content_type=photo.content_type)

        # Make the blob publicly viewable.
        blob.make_public()
        image_public_url = blob.public_url
        
        # Create a Cloud Vision client.
        vision_client = vision.ImageAnnotatorClient()

        # Retrieve a Vision API response for the photo stored in Cloud Storage
        image = vision.types.Image()
        image.source.image_uri = 'gs://{}/{}'.format(os.environ.get('CLOUD_STORAGE_BUCKET'), blob.name)
        
        response = vision_client.annotate_image({'image': image})
        labels = response.label_annotations
        faces = response.face_annotations
        web_entities = response.web_detection.web_entities

        # Create a Cloud Firestore client
        firestore_client = firestore.Client()

        # Get a reference to the document we will upload to
        doc_ref = firestore_client.collection(u'photos').document(blob.name)

        # Note: If we are using Python version 2, we need to convert
        # our image URL to unicode to save it to Cloud Firestore properly.
        if sys.version_info < (3, 0):
            image_public_url = unicode(image_public_url, "utf-8")

        # Construct key/value pairs with data
        data = {
            u'image_public_url': image_public_url,
            u'top_label': labels[0].description
        }

        # Set the document with the data
        doc_ref.set(data)

        # Redirect to the home page.
        return render_template('image_scan.html', labels=labels, faces=faces, web_entities=web_entities, image_public_url=image_public_url)


@app.route('/page_scan')
def page_scan():
    # Redirect to the home page.
    return render_template('upload_page.html')

@app.route('/scan_url', methods=['GET', 'POST'])
def scan_url():
    # If the user inputs a site's link
    if request.form["site-link"]:
        page_link = request.form["site-link"]
        image_links = get_all_images(page_link)

        all_images = {} # hold all images information
        all_images["no_alt"] = [] # hold all images with no_alt
        all_images["possible_decorative"] = []
        all_images["warnings"] = []

        no_alt_images = image_links["no_alt"] # get array of images with no alt text attribute
        for single_image in no_alt_images:
            image_public_url = single_image["url"] # get the image's src
            client = vision.ImageAnnotatorClient()
            image = vision.types.Image()
            image.source.image_uri = image_public_url

            response = client.label_detection(image=image)

            labels = response.label_annotations
            if labels: 
                image_details = {}
                image_details["url"] = image_public_url
                image_details["alt"] = single_image["alt"]
                image_details["warning"] = single_image["warning"]
                image_details["labels"] = labels
                all_images["no_alt"].append(image_details) # save details to no_alt

        
        possible_decorative_images = image_links["possible_decorative"] # get array of images that have empty alt text (could be decorative image)
        for single_image in possible_decorative_images:
            image_public_url = single_image["url"] # get the image's src
            client = vision.ImageAnnotatorClient()
            image = vision.types.Image()
            image.source.image_uri = image_public_url

            response = client.label_detection(image=image)

            labels = response.label_annotations
            if labels: 
                image_details = {}
                image_details["url"] = image_public_url
                image_details["alt"] = single_image["alt"]
                image_details["warning"] = single_image["warning"]
                image_details["labels"] = labels
                all_images["possible_decorative"].append(image_details) # save details to possible_decorative
        
        index_count = 0 # start index count at 0
        warning_images = image_links["warnings"] # get array of images that might have bad alt text
        for single_image in warning_images:
            image_public_url = single_image["url"] # get the image's src
            client = vision.ImageAnnotatorClient()
            image = vision.types.Image()
            image.source.image_uri = image_public_url

            response = client.label_detection(image=image)

            labels = response.label_annotations
            if labels: 
                image_details = {}
                image_details["url"] = image_public_url
                image_details["alt"] = single_image["alt"]
                image_details["warning"] = single_image["warning"]
                image_details["labels"] = labels
                all_images["warnings"].append(image_details) # save details to warnings

        # Organize data for passing
        no_alt_images = all_images["no_alt"] # get array of images with no alt text attribute
        possible_decorative_images = all_images["possible_decorative"] # get array of images that have empty alt text (could be decorative image)
        warning_images = all_images["warnings"] # get array of images that might have bad alt text
        
        # Redirect to the scan page.
        return render_template('scan_page.html', no_alt_images=no_alt_images, possible_decorative_images=possible_decorative_images, warning_images=warning_images, page_link=page_link, image_links=image_links)

@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)