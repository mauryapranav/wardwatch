/// WardWatch - API Service
/// HTTP client for communicating with the WardWatch Cloud Run backend.
/// Uses Firebase Auth token for all authenticated requests.
/// Base URL is configured via Firebase Remote Config or app config (NOT hardcoded).
library;

import 'dart:convert';
import 'dart:io';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:http/http.dart' as http;

/// WardWatch API client.
/// All secrets (Maps key, etc.) are handled server-side.
class ApiService {
  // Base URL — must be set before use.
  // In production: set from build config (not hardcoded).
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8080', // Android emulator localhost
  );

  /// Get the current user's Firebase ID token.
  Future<String?> _getIdToken() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      return await user?.getIdToken(true);
    } catch (e) {
      return null;
    }
  }

  /// Build authenticated headers.
  Future<Map<String, String>> _authHeaders() async {
    final token = await _getIdToken();
    final appCheckToken = await FirebaseAppCheck.instance.getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
      if (appCheckToken != null) 'X-Firebase-AppCheck': appCheckToken,
    };
  }

  /// GET request with auth.
  Future<Map<String, dynamic>> get(String path, {Map<String, String>? queryParams}) async {
    final uri = Uri.parse('$_baseUrl$path').replace(queryParameters: queryParams);
    final headers = await _authHeaders();
    final response = await http.get(uri, headers: headers).timeout(const Duration(seconds: 30));
    return _handleResponse(response);
  }

  /// POST request with auth.
  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('$_baseUrl$path');
    final headers = await _authHeaders();
    final response = await http.post(
      uri,
      headers: headers,
      body: body != null ? jsonEncode(body) : null,
    ).timeout(const Duration(seconds: 30));
    return _handleResponse(response);
  }

  /// PUT request with auth.
  Future<Map<String, dynamic>> put(String path, {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('$_baseUrl$path');
    final headers = await _authHeaders();
    final response = await http.put(
      uri,
      headers: headers,
      body: body != null ? jsonEncode(body) : null,
    ).timeout(const Duration(seconds: 30));
    return _handleResponse(response);
  }

  /// Upload a file (multipart).
  Future<Map<String, dynamic>> uploadFile(String path, File file) async {
    final uri = Uri.parse('$_baseUrl$path');
    final token = await _getIdToken();
    final appCheckToken = await FirebaseAppCheck.instance.getToken();
    final request = http.MultipartRequest('POST', uri);
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }
    if (appCheckToken != null) {
      request.headers['X-Firebase-AppCheck'] = appCheckToken;
    }
    request.files.add(await http.MultipartFile.fromPath('file', file.path));
    final streamedResponse = await request.send().timeout(const Duration(seconds: 60));
    final response = await http.Response.fromStream(streamedResponse);
    return _handleResponse(response);
  }

  /// Get campaign by ID (GET /api/v1/issues/{id}).
  Future<Map<String, dynamic>> getCampaignById(String id) async {
    return get('/api/v1/issues/$id');
  }

  /// Upload a photo with optional metadata.
  /// For hackathon: delegates to uploadFile. Campaign/type metadata is stored client-side.
  Future<Map<String, dynamic>> uploadPhoto(
    File file, {
    String? campaignId,
    String? photoType,
  }) async {
    return uploadFile('/api/v1/upload', file);
  }

  Map<String, dynamic> _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    // Parse error message
    String detail = 'An error occurred. Please try again.';
    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      detail = body['detail'] as String? ?? detail;
    } catch (_) {}
    throw ApiException(statusCode: response.statusCode, message: detail);
  }
}

/// API exception with status code and user-friendly message.
class ApiException implements Exception {
  final int statusCode;
  final String message;
  const ApiException({required this.statusCode, required this.message});

  @override
  String toString() => 'ApiException($statusCode): $message';
}

/// Singleton instance
final apiService = ApiService();
