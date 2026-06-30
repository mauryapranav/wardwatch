/// WardWatch - Camera Screen (Step 1.11)
/// Captures photos and GPS, uploads to backend.
/// Reverse geocoding is done via backend API (not direct Maps API from Flutter).
library;

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import '../services/api_service.dart';
import 'create_campaign_screen.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  bool _isInitialized = false;
  bool _isCapturing = false;
  bool _isUploading = false;
  File? _capturedImage;
  Position? _gpsPosition;
  String _address = '';
  double _uploadProgress = 0.0;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    // Request camera permission
    final permission = await _requestCameraPermission();
    if (!permission) {
      setState(() => _errorMessage = 'Camera permission is required to report issues.');
      return;
    }

    try {
      _cameras = await availableCameras();
      if (_cameras.isEmpty) {
        setState(() => _errorMessage = 'No camera found on this device.');
        return;
      }

      _controller = CameraController(
        _cameras.first,
        ResolutionPreset.high,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );

      await _controller!.initialize();
      if (!mounted) return;
      setState(() => _isInitialized = true);
    } catch (e) {
      setState(() => _errorMessage = 'Failed to initialize camera.');
    }
  }

  Future<bool> _requestCameraPermission() async {
    final status = await Permission.camera.request();
    return status.isGranted;
  }

  Future<void> _capturePhoto() async {
    if (_controller == null || !_controller!.value.isInitialized || _isCapturing) return;

    setState(() {
      _isCapturing = true;
      _errorMessage = '';
    });

    try {
      // Capture GPS simultaneously
      Position? gps;
      try {
        gps = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 10),
        );
      } catch (_) {
        // GPS failed or permission denied — continue without exact location
        gps = null;
      }

      // Take photo
      final XFile imageFile = await _controller!.takePicture();

      // Get address via backend (not direct Maps API)
      String address = 'Address unavailable';
      if (gps != null) {
        try {
          final geocodeResult = await apiService.get(
            '/api/v1/geo/reverse',
            queryParams: {
              'lat': gps.latitude.toString(),
              'lng': gps.longitude.toString(),
            },
          );
          address = geocodeResult['address'] as String? ?? 'Address not found';
        } catch (_) {
          address = 'Address unavailable';
        }
      }

      setState(() {
        _capturedImage = File(imageFile.path);
        _gpsPosition = gps;
        _address = address;
        _isCapturing = false;
      });
    } catch (e) {
      setState(() {
        _isCapturing = false;
        _errorMessage = 'Failed to capture photo. Please try again.';
      });
    }
  }

  Future<void> _confirmAndUpload() async {
    if (_capturedImage == null || _gpsPosition == null) return;

    setState(() {
      _isUploading = true;
      _uploadProgress = 0.0;
      _errorMessage = '';
    });

    try {
      // Upload to backend
      final result = await apiService.uploadFile('/api/v1/upload', _capturedImage!);

      final storagePath = result['storage_path'] as String;
      final photoId = result['storage_path']?.toString().split('/').last ?? '';

      // Clean up temp file
      try {
        await _capturedImage!.delete();
      } catch (_) {}

      if (!mounted) return;

      // Navigate to create campaign screen
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => CreateCampaignScreen(
            storagePath: storagePath,
            photoId: photoId,
            gpsLat: _gpsPosition!.latitude,
            gpsLng: _gpsPosition!.longitude,
            address: _address,
          ),
        ),
      );
    } catch (e) {
      setState(() {
        _isUploading = false;
        _errorMessage = e is ApiException ? e.message : 'Upload failed. Please try again.';
      });
    }
  }

  void _retake() {
    // Delete captured image and go back to preview
    _capturedImage?.delete();
    setState(() {
      _capturedImage = null;
      _gpsPosition = null;
      _address = '';
      _errorMessage = '';
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_errorMessage.isNotEmpty && !_isInitialized) {
      return Scaffold(
        appBar: AppBar(title: const Text('Report Issue')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.camera_alt_outlined, size: 64, color: Colors.grey),
                const SizedBox(height: 16),
                Text(_errorMessage, textAlign: TextAlign.center),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _initCamera,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (_capturedImage != null) {
      return _buildPreviewScreen();
    }

    return _buildCameraScreen();
  }

  Widget _buildCameraScreen() {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Report Issue'),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
      ),
      body: !_isInitialized
          ? const Center(child: CircularProgressIndicator(color: Colors.white))
          : Stack(
              children: [
                CameraPreview(_controller!),
                // Capture button
                Positioned(
                  bottom: 40,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: GestureDetector(
                      onTap: _isCapturing ? null : _capturePhoto,
                      child: Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 4),
                          color: _isCapturing ? Colors.grey : Colors.white,
                        ),
                        child: _isCapturing
                            ? const CircularProgressIndicator()
                            : const Icon(Icons.camera_alt, size: 36, color: Colors.black87),
                      ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildPreviewScreen() {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Confirm Photo'),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _retake,
        ),
      ),
      backgroundColor: Colors.black,
      body: Column(
        children: [
          Expanded(
            child: Image.file(_capturedImage!, fit: BoxFit.contain),
          ),
          // Location info
          Container(
            color: Colors.black87,
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_gpsPosition != null)
                  Text(
                    'GPS: ${_gpsPosition!.latitude.toStringAsFixed(6)}, ${_gpsPosition!.longitude.toStringAsFixed(6)}',
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                const SizedBox(height: 4),
                Text(
                  _address,
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                  maxLines: 2,
                ),
                if (_errorMessage.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(_errorMessage, style: const TextStyle(color: Colors.red, fontSize: 13)),
                ],
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isUploading ? null : _retake,
                        icon: const Icon(Icons.refresh, color: Colors.white),
                        label: const Text('Retake', style: TextStyle(color: Colors.white)),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Colors.white54),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: _isUploading ? null : _confirmAndUpload,
                        icon: _isUploading
                            ? const SizedBox(
                                height: 16,
                                width: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.upload),
                        label: Text(_isUploading ? 'Uploading...' : 'Confirm'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1565C0),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }
}
