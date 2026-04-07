# Quick Start Guide - Ambient Listening Pipeline

## Getting Started in 4 Steps

### 1. Install Dependencies
```bash
cd Ambient-AI-Solution
pip install -r requirements.txt
```

### 2. Configure AWS Credentials
The application uses Amazon Bedrock Nova Pro for AI-powered SOAP note generation.

**Quick Setup (AWS CLI):**
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region: us-east-1
```

**Or set environment variables:**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 3. Enable Bedrock Model Access
1. Go to [AWS Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Click "Model access" in the left sidebar
3. Click "Manage model access"
4. Enable "Amazon Nova Pro"
5. Click "Save changes"

### 4. Run the Application
```bash
python app.py
```

Then open: **http://localhost:5001**

## Using the Pipeline

### Step 1: Transcript Input
- Click **"Load Sample Transcript"** to load demo data
- Or paste your own medical transcript
- Click **"Generate SOAP Note"**

### Step 2: SOAP Note
- Review the AI-generated SOAP note from Amazon Bedrock Nova Pro
- Sections: Subjective, Objective, Assessment, Plan
- Click **"Extract Entities"**

### Step 3: Entity Extraction
- View extracted entities categorized as:
  - 🔴 Problems/Diagnoses
  - 🟢 Procedures
  - 🟠 Medications
  - 🔵 Lab Results
- Click **"Normalize with IMO"**

### Step 4: IMO Normalization
- View normalized entities with IMO codes
- Entities marked with ⚠️ need refinement
- Click **"Refine Entities"** if available

### Step 5: Refinement
- Select refinement options for entities needing additional specificity
- Choose the most appropriate refined concept

## Demo Mode

The application includes a **fallback mechanism**:
- ✅ If AWS Bedrock is unavailable, uses rule-based SOAP generation
- ✅ Works without API credentials for IMO APIs (uses demo mode)
- ✅ Perfect for testing and demos

## Production Mode

### For AI-Powered SOAP Notes:
1. Configure AWS credentials (see step 2 above)
2. Enable Bedrock Nova Pro model access (see step 3 above)
3. Restart the application

### For Live IMO APIs:

1. Get API credentials from https://developer.imohealth.com

2. Edit `config.py`:
```python
imo_api_key = "YOUR_ACTUAL_API_KEY"
imo_client_id = "YOUR_CLIENT_ID"
imo_client_secret = "YOUR_CLIENT_SECRET"
demo_mode = False
```

3. Restart the application

## Troubleshooting

**Port already in use?**
- Edit `app.py` and change `port=5001` to another port

**Dependencies missing?**
```bash
pip install flask requests
```

**Can't find templates?**
- Make sure you're running from the Ambient-AI-Solution directory

## Features

✨ **AI-Powered SOAP Generation**: Uses Amazon Bedrock Nova Pro for intelligent medical note generation  
📊 **Pipeline Flow**: Visual step-by-step progress indicator  
📝 **Expert System Prompt**: "I am an expert SOAP note generator. Given a medical transcript of inpatient or outpatient visits I can create a SOAP note."  
🔍 **Entity Extraction**: Identifies medical concepts automatically  
💾 **IMO Normalization**: Standardizes codes to IMO terminology  
⚙️ **Refinement**: Adds specificity to ambiguous entities  
🔄 **Fallback Support**: Works even if Bedrock is unavailable

## Sample Transcript Included

The application includes a realistic medical transcript featuring:
- Patient presentation with chest pain
- Complete medical history
- Physical examination findings
- Diagnostic test results
- Assessment and treatment plan

Perfect for testing all pipeline features!

## Next Steps

1. Try the sample transcript
2. Test with your own ambient listening transcripts
3. Configure IMO API credentials for production use
4. Customize entity categories and refinement logic as needed

---

**Need Help?** Check README.md for detailed documentation.
