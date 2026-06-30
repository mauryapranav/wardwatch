/// WardWatch - Join Campaign Screen (Step 1.15)
/// Shows existing nearby campaign and prompts user to join.
library;

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'campaign_detail_screen.dart';

class JoinCampaignScreen extends StatefulWidget {
  final String highlightCampaignId;
  final String message;

  const JoinCampaignScreen({
    super.key,
    required this.highlightCampaignId,
    required this.message,
  });

  @override
  State<JoinCampaignScreen> createState() => _JoinCampaignScreenState();
}

class _JoinCampaignScreenState extends State<JoinCampaignScreen> {
  Map<String, dynamic>? _campaign;
  bool _isLoading = true;
  bool _isJoining = false;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _fetchCampaign();
  }

  Future<void> _fetchCampaign() async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });
    try {
      final result = await apiService.get('/api/v1/issues/${widget.highlightCampaignId}');
      setState(() {
        _campaign = result;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to load campaign details.';
      });
    }
  }

  Future<void> _joinCampaign() async {
    setState(() => _isJoining = true);
    try {
      await apiService.post('/api/v1/issues/${widget.highlightCampaignId}/join');
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => CampaignDetailScreen(campaignId: widget.highlightCampaignId),
        ),
      );
    } on ApiException catch (e) {
      setState(() => _isJoining = false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Similar Issue Found'),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Info card
                  Card(
                    color: Colors.orange[50],
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          const Icon(Icons.info_outline, color: Colors.orange),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              widget.message,
                              style: const TextStyle(fontSize: 14),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),

                  if (_errorMessage.isNotEmpty)
                    Text(_errorMessage,
                        style: const TextStyle(color: Colors.red))
                  else if (_campaign != null) ...[
                    Text(
                      _campaign!['title'] ?? 'Existing Campaign',
                      style: const TextStyle(
                          fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _campaign!['description'] ?? '',
                      style: const TextStyle(color: Colors.black54),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Chip(
                          label: Text(_campaign!['issue_type'] ?? ''),
                          backgroundColor: Colors.blue[50],
                        ),
                        const SizedBox(width: 8),
                        Chip(
                          label: Text(
                              '${_campaign!['citizen_count'] ?? 0} citizens'),
                          backgroundColor: Colors.green[50],
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Icon(Icons.location_on,
                            size: 16, color: Colors.red),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            _campaign!['address'] ?? '',
                            style: const TextStyle(
                                fontSize: 13, color: Colors.black54),
                          ),
                        ),
                      ],
                    ),
                  ],

                  const Spacer(),

                  // Action buttons
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: _isJoining ? null : _joinCampaign,
                      icon: _isJoining
                          ? const SizedBox(
                              height: 16,
                              width: 16,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.group_add),
                      label:
                          Text(_isJoining ? 'Joining...' : 'Join This Campaign'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1565C0),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12)),
                      ),
                      child: const Text('Go Back'),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }
}
