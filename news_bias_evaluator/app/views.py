from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import cache_page
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .utils import convert_label_bias, decode_utf8, extractSentences, is_non_empty_sentence, is_valid_label_bias, is_valid_news_link, getFromJson, getModelVersion, getPredictionArrays, sendRequest, getModels, softmax
from app.retraining_utils import training_handler, training_job_monitor, database_bucket_sync, training_evaluation_retriever, retrained_model_deployer
from django.http import HttpResponse
from asgiref.sync import async_to_sync, sync_to_async
from django.http import JsonResponse
import os
import csv
import logging
import json
from transformers import DistilBertTokenizerFast, AutoModelForSequenceClassification
import numpy as np
from transformers_interpret import SequenceClassificationExplainer
from app.templatetags.evaluation import getBatchPrediction, saveEvaluationData

cwd = os.getcwd()  # Get the current working directory (cwd)
from .models import Article, LabeledSentence, ModelEvaluation, Request, Prediction

dashboard_context = {}

# Views for user side
def main(request):
    return render(request, 'app/main.html')

# Cache the response for 10 minutes
@cache_page(60 * 10)
def onSubmit(request):
    items = {}
    file = open(cwd+"/modelSettings.json", "r")
    data = json.load(file)
    file.close()

    text_input = request.GET['input-text'] # retrieve the text input from form
    model_name = data['prediction_model'] 
    print("Model name: " + model_name)
    sentenceList = extractSentences(text_input)

    # Get the explanations for the sentences
    explanations = onGetExplanation(sentenceList)

   # Get the prediction input ids for the sentences
    predictionInput = getPredictionArrays(sentenceList)

    # Saves the request into the DB
    user_request = Request(request_content = text_input)
    user_request.save()
    
    if(len(sentenceList) > 0):
        predictionList = sendRequest(predictionInput, model_name)
        normalised = softmax(predictionList)

        # Saves the prediction in the DB, using the request
        prediction = Prediction (request = user_request, prediction = predictionList)
        prediction.save()

        # Update the status of the request to processed since we received a prediction (allows to have easy stats on reliability)
        user_request.processed = True
        user_request.save
    try:
        if (len(sentenceList) > 0 and len(sentenceList) == len(predictionList)):
            items = {sentenceList[i]: { 'prediction': normalised[i][np.argmax(normalised[i])], 'label': np.argmax(normalised[i]), 'input_id': explanations[str(i+1)] }for i in range(len(sentenceList))}
    except:
        messages.error(request, "Failed to get a response from the selected model!")
 
    # creates a context (dictionary mapping variables to HTML variables)
    context = {
        'resultList': items
    }

    return render(request, 'app/results.html', context)

def onModelChange(selected_model, isPrediction):
    isUpdated = False
    try:
        with open(cwd+'/modelSettings.json', errors="ignore") as file:
            data = json.load(file)
            file.close()

        if(isPrediction):
            data['prediction_model'] = selected_model
        else:
            data['evaluation_model'] = selected_model

        file = open(cwd+'/modelSettings.json', "w")
        json.dump(data, file)
        file.close()
        isUpdated = True
    except:
        print("Failed to save the model in the JSON file!")
    return isUpdated

# Gets the tokenized sentences and their corresponding weights pertaining to the prediction
def onGetExplanation(sentences):
    model_name = "distilbert-base-uncased"
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    tokenizer = DistilBertTokenizerFast.from_pretrained(model_name)
    cls_explainer = SequenceClassificationExplainer(
        model,
        tokenizer)

    tokenizedExplanation = {}
    count = 1
    for sentence in sentences:
        word_attributions = cls_explainer(sentence)
        tokenizedExplanation[str(count)] = dict(word_attributions)
        count += 1
    return tokenizedExplanation

# views for admin side
@login_required # decorator redirecting to the login page defined in settings.py if no user is logged in
def dispatch(request):
        return redirect('app:dashboard')

def log(request):
    '''
    Method rendering the login page
    '''
    return render(request, 'app/login.html')

def log_out(request):
    logout(request)
    return redirect('app:main')
 
def access_dashboard(request):
    '''
    method that process a login request.
    If the user is found with the right credentials, it redirects to the dashboard
    in other cases, it returns to the login page and a message to the user is created.
    '''
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)

        # Retrieve all info to be displayed in the dashboard
        # list of models. Need to be added in this variable
        model_list= getModels()
        if(len(model_list) == 0):
            messages.error(request, "Failed to connect to google cloud!")

        print(model_list)
        # generates the graph using matplotlib here more info -> https://medium.com/@mdhv.kothari99/matplotlib-into-django-template-5def2e159997
        
        img_uri = 'some_parsed_uri'

        context = {
            'models': model_list,
            'img': img_uri,            
        }

        return render(request, "app/dashboard.html", context)
    else:
        messages.info(request, 'Incorrect password or username.')
        return redirect('app:login')

@login_required
def process_admin_request(request):
    type_of_request = request.POST.get('action-selection')
    selected_model = request.POST.get('model-options')
    print(type_of_request)
    print(selected_model)

    if(type_of_request == 'evaluate'):
       context = {
            'evaluation' : process_evaluation_request(request, selected_model)
       }
       return render(request, 'app/evaluation.html', context)
    elif(type_of_request == 'retrain'):
        onModelChange(selected_model, False)
        print('entering retrain')
        # Sync database and cloud bucket
        database_bucket_sync.sync_db_and_bucket()
        # This execution will initiate the training job, it DOES NOT
        # wait for a successful/failed training job!
        training_response, job_name = training_handler.runTrainingJob()
        print(training_response)
        print('exited retrain job')            
        # Pass via a context the job name.
        return render(request, 'app/retrain.html', {'job_name': job_name })
    elif(type_of_request == 'use-selected'):
        if(onModelChange(selected_model, True)):
            messages.success(request, 'Model successfully changed!')
        else:
            messages.error(request, 'Failed to change the model!')
        context ={
            'models': getModels(),
        }

        return render(request, "app/dashboard.html", context) 
    else:
        return redirect('app:main')

@sync_to_async
@login_required
@async_to_sync
async def get_training_status(request):
    job_name = request.GET.get('job_name', None) 
    status_response = training_job_monitor.getStatus(job_name)
    print(status_response)
    # insert data from ai platform here.
    return JsonResponse(status_response)
    
@login_required
def process_evaluation_request(request, selected_model):
    data = getBatchPrediction(selected_model)
    onModelChange(selected_model, False)
    saveEvaluationData(data)
    return data

@login_required
def get_training_evaluation_data(request):
    training_evaluation_data = training_evaluation_retriever.get_training_evaluation_data()
    # TODO: Use saved data from database in AP-47 instead of getBatchPrediction()!
    latest_model_evaluation_data = getBatchPrediction(getFromJson("evaluation_model"))
    # combine the eval data with accuracy, precision etc.
    latest_model_evaluation_data = training_evaluation_retriever.combine_metrics(latest_model_evaluation_data)
    # Create json object to send both evaluations
    response_evaluation_data = {'training_evaluation_data': training_evaluation_data, 'latest_model_evaluation_data': latest_model_evaluation_data}
    print('getting training eval data')
    return JsonResponse(response_evaluation_data, content_type='application/json')

@login_required
def handle_deployment_choice(request):
    # get a deployment request
    deployment_choice = request.POST.get('choice')
    # if the deployment is true, deploy a new version of the simple model.
    if deployment_choice == 'true':
        status, model_name = retrained_model_deployer.deploy_model()
        # onModelChange('projects/dit825/models/simple_model/versions/'+model_name) 
        return HttpResponse(status)
    else:
        return HttpResponse()

def upload_csv(request):
    #get the csv file
    try:
        csv_file = request.FILES["csv_file"]
        #if file is not csv, return
        if not csv_file.name.endswith('.csv'):
            messages.error(request,'File is not CSV type')
            return
        #if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(request,"Uploaded file is too big (%.2f MB)." % (csv_file.size/(1000*1000),))
            return
    # if error with upload occurs, display error message
    except Exception as e:
        logging.getLogger("error_logger").error("Unable to upload csv file. " + repr(e))
        messages.error(request,"Unable to upload csv file. " + repr(e))

    # if no errors, read the csv file as a dictionary
    reader = csv.DictReader(decode_utf8(csv_file))
    
    count = 0
    result = ""
	#loop over the lines and save them in db
    for row in reader:
        news_link = row['news_link']
        outlet=row['outlet']
        sentence=row['sentence']
        label_bias=row['label']
        pub_year = row['pub_year']
        filename = csv_file.name

        # checks to see if data is valid, if so, saves it to the database
        if(is_valid_news_link(news_link) and is_non_empty_sentence(sentence) and is_valid_label_bias(label_bias)):
            new_article = Article(
                news_link=news_link,
                outlet=outlet, 
                pub_year=pub_year,
            )
            new_article.save()

            new_sentence = LabeledSentence(
                    sentence=sentence,
                    label_bias=convert_label_bias(label_bias), # converts the label_bias to number format
                    article = new_article,
                    filename = filename,
            )
            new_sentence.save()
            count += 1

    context = {
        'result': "Successful upload",
        'amount': count,
        'file': csv_file.name,
    }

    return render(request, "app/dashboard.html", context)
