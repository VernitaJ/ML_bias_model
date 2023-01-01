from django import template
from app.models import LabeledSentence
from django.http import JsonResponse
import os
import json

from app.utils import sendRequest

register = template.Library()

@register.simple_tag
def getBatchPrediction():
    dataPoints = LabeledSentence.objects.all()[-50:]
    sentenceList = [data.sentence for data in dataPoints]
    currentModel = getModelName()
    evaluationResults = sendRequest(sentenceList, currentModel)

    results = {}
    results = {dataPoints[i].sentence: { 'true_value' : dataPoints[i].label_bias, 'predicted_value' : evaluationResults[i][0]} for i in range(len(sentenceList))}

    evaluationResults = getEvaluationResults(results, currentModel)
    return evaluationResults

@register.simple_tag
def saveEvaluationData(data):
    evaluation = { 'name': getModelName(), 'true_positive': data['true_positive'], 'false_positive': data['false_positive'], 'false_negative': data['false_negative'], 'true_negative': data['true_negative']}
    print(evaluation)
   
@register.simple_tag
def getModelName():
    cwd = os.getcwd()  # Get the current working directory (cwd)
    with open(cwd+'/modelSettings.json', errors="ignore") as file:
        data = json.load(file)
        file.close()
        model_name = data['name'] 
    return model_name

@register.simple_tag
def getEvaluationResults(results, currentModel):
    TN = 0
    TP = 0
    FP = 0
    FN = 0
    for result in results.items():
        if (result[1]['true_value'] == 'Biased'): 
            if (result[1]['predicted_value'] < 0.5):
                TP += 1
            else: FN += 1
        elif (result[1]['true_value'] == 'Non-biased'):
            if (result[1]['predicted_value'] >= 0.5):
                TN += 1
            else: FP += 1
    return {'true_positive':TP, 'true_negative':TN, 'false_positive': FP, 'false_negative': FN, 'model': currentModel}

@register.simple_tag
def getAccuracy(evaluation):
    total = evaluation['true_positive'] + evaluation['false_positive'] + evaluation['true_negative'] + evaluation['false_negative']
    accuracy = (evaluation['true_positive'] + evaluation['true_negative']) / total
    return f"{accuracy * 100:.2f}"

@register.simple_tag
def getPrecision(evaluation):
    precision = evaluation['true_positive'] / (evaluation['false_positive'] + evaluation['true_positive'])
    return f"{precision * 100:.2f}"

@register.simple_tag
def getNegPrecision(evaluation):
    precision = evaluation['true_negative'] / (evaluation['true_negative'] + evaluation['false_negative'])
    return f"{precision * 100:.2f}"

@register.simple_tag
def getRecall(evaluation):
    recall = evaluation['true_positive'] / (evaluation['true_positive'] + evaluation['false_negative'])
    return f"{recall * 100:.2f}"