{{/*
Expand the name of the chart.
*/}}
{{- define "oh-staff.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "oh-staff.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "oh-staff.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "oh-staff.labels" -}}
helm.sh/chart: {{ include "oh-staff.chart" . }}
{{ include "oh-staff.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "oh-staff.selectorLabels" -}}
app.kubernetes.io/name: {{ include "oh-staff.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Deployment Volume Configuration
*/}}
{{- define "oh-staff.volumes" -}}
- name: "ohsource"
  persistentVolumeClaim:
    claimName: {{ include "oh-staff.fullname" . }}-pvc-ohsource
- name: "ohmasters"
  persistentVolumeClaim:
    claimName: {{ include "oh-staff.fullname" . }}-pvc-ohmasters
- name: "ohmasterslz"
  persistentVolumeClaim:
    claimName: {{ include "oh-staff.fullname" . }}-pvc-ohmasterslz
- name: "ohwowza"
  persistentVolumeClaim:
    claimName: {{ include "oh-staff.fullname" . }}-pvc-ohwowza
- name: "ohstatic"
  persistentVolumeClaim:
    claimName: {{ include "oh-staff.fullname" . }}-pvc-ohstatic
{{- end }}