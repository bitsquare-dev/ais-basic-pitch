# Basic Pitch API for Coolify

Audio-to-MIDI conversion service using Spotify's Basic Pitch model.

## Coolify Setup

1. Create a new application in Coolify
2. Select **Docker Compose** as the build method
3. Point to this repository
4. Deploy

The service will be available at your configured domain on port 8000.

## API Endpoints

### Health Check
```
GET /health
```

### Convert Audio to MIDI (Base64 response)
```
POST /predict
Content-Type: multipart/form-data

file: <audio file>
```

Returns JSON with base64-encoded MIDI:
```json
{
  "midi_base64": "TVRoZC...",
  "filename": "song.mid"
}
```

### Convert Audio to MIDI (File response)
```
POST /predict/file
Content-Type: multipart/form-data

file: <audio file>
```

Returns the MIDI file directly.

## Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| onset_threshold | 0.5 | Note onset detection threshold (0-1) |
| frame_threshold | 0.3 | Frame detection threshold (0-1) |
| minimum_note_length | 58.0 | Minimum note length in ms |
| minimum_frequency | None | Minimum frequency in Hz |
| maximum_frequency | None | Maximum frequency in Hz |

## n8n Integration

### Using HTTP Request Node

1. Add an **HTTP Request** node
2. Configure:
   - **Method**: POST
   - **URL**: `http://basic-pitch:8000/predict`
   - **Body Content Type**: Form-Data/Multipart
   - **Body Parameters**: Add `file` parameter with your audio binary

3. The response contains `midi_base64` which you can decode

### Example n8n Workflow (JSON)

```json
{
  "nodes": [
    {
      "name": "HTTP Request",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://basic-pitch:8000/predict",
        "sendBody": true,
        "contentType": "multipart-form-data",
        "bodyParameters": {
          "parameters": [
            {
              "name": "file",
              "parameterType": "formBinaryData",
              "inputDataFieldName": "data"
            }
          ]
        }
      }
    }
  ]
}
```

### Decoding MIDI in n8n

Use a **Code** node to decode the base64 MIDI:

```javascript
const midiBase64 = $input.first().json.midi_base64;
const binaryData = Buffer.from(midiBase64, 'base64');

return {
  binary: {
    data: {
      data: binaryData.toString('base64'),
      mimeType: 'audio/midi',
      fileName: $input.first().json.filename
    }
  }
};
```

## Network Configuration

Since both n8n and basic-pitch run on the same server in Coolify:

1. Ensure both services are on the same Docker network (Coolify handles this)
2. Use the container name `basic-pitch` as the hostname
3. Internal URL: `http://basic-pitch:8000`

## Supported Audio Formats

- WAV
- MP3
- OGG
- FLAC
- M4A
