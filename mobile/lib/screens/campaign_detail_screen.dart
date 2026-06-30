/// WardWatch - Campaign Detail Screen (Step 1.14)
library;

import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:share_plus/share_plus.dart';
import '../services/api_service.dart';
import '../widgets/sla_countdown.dart';
import '../widgets/escalation_timeline.dart';

class CampaignDetailScreen extends StatefulWidget {
  final String campaignId;

  const CampaignDetailScreen({super.key, required this.campaignId});

  @override
  State<CampaignDetailScreen> createState() => _CampaignDetailScreenState();
}

class _CampaignDetailScreenState extends State<CampaignDetailScreen> {
  Map<String, dynamic>? _campaign;
  bool _isLoading = true;
  bool _isJoining = false;
  String _errorMessage = '';
  bool _isMember = false;

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
      final result = await apiService.get('/api/v1/issues/${widget.campaignId}');
      setState(() {
        _campaign = result;
        _isLoading = false;
        // Determine if user is a member (if member endpoint returns this info)
      });
    } on ApiException catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = e.statusCode == 403
            ? 'You are not a member of this campaign.'
            : e.statusCode == 404
                ? 'Campaign not found.'
                : e.message;
      });
    } catch (_) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to load campaign. Please try again.';
      });
    }
  }

  Future<void> _joinCampaign() async {
    setState(() => _isJoining = true);
    try {
      await apiService.post('/api/v1/issues/${widget.campaignId}/join');
      setState(() {
        _isMember = true;
        _isJoining = false;
      });
      await _fetchCampaign();
    } on ApiException catch (e) {
      setState(() => _isJoining = false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.message),
          backgroundColor: e.statusCode == 400 ? Colors.orange : Colors.red,
        ),
      );
    }
  }

  void _shareCampaign() {
    final title = _campaign?['title'] ?? 'Civic Issue';
    final status = _campaign?['status'] ?? 'open';
    final count = _campaign?['citizen_count'] ?? 0;
    Share.share(
      'Join me on WardWatch! Campaign: $title\n'
      'Status: $status | $count citizens\n'
      'Campaign ID: ${widget.campaignId}',
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_campaign?['title'] ?? 'Campaign Details'),
        backgroundColor: const Color(0xFF1565C0),
        foregroundColor: Colors.white,
        actions: [
          if (_campaign != null)
            IconButton(
              icon: const Icon(Icons.share),
              onPressed: _shareCampaign,
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage.isNotEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 64, color: Colors.grey),
                        const SizedBox(height: 16),
                        Text(_errorMessage, textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: _fetchCampaign,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : _buildContent(),
    );
  }

  Widget _buildContent() {
    final c = _campaign!;
    final status = c['status'] as String? ?? 'open';
    final citizenCount = c['citizen_count'] as int? ?? 0;
    final slaDl = c['sla_deadline'] as String?;
    final timeline = (c['timeline'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ?? [];
    final photos = (c['photos'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ?? [];

    // Firestore real-time listener (on top of REST data)
    return StreamBuilder<DocumentSnapshot>(
      stream: FirebaseFirestore.instance
          .collection('campaigns')
          .doc(widget.campaignId)
          .snapshots(),
      builder: (context, snapshot) {
        final liveCount = snapshot.hasData
            ? (snapshot.data!.data() as Map<String, dynamic>?)?['citizen_count'] ?? citizenCount
            : citizenCount;

        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Status badge
              Row(
                children: [
                  _statusBadge(status),
                  const Spacer(),
                  Row(
                    children: [
                      const Icon(Icons.people, size: 18, color: Colors.blue),
                      const SizedBox(width: 4),
                      Text('$liveCount citizens',
                          style: const TextStyle(fontWeight: FontWeight.bold)),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // Title & description
              Text(c['title'] ?? '',
                  style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(c['description'] ?? '',
                  style: const TextStyle(fontSize: 15, color: Colors.black54)),
              const SizedBox(height: 12),

              // Issue type + severity
              Row(
                children: [
                  Chip(
                    label: Text((c['issue_type'] as String? ?? '').toUpperCase(),
                        style: const TextStyle(fontSize: 12)),
                    backgroundColor: Colors.blue[50],
                  ),
                  const SizedBox(width: 8),
                  Row(
                    children: List.generate(
                      5,
                      (i) => Icon(
                        i < (c['severity'] as int? ?? 0)
                            ? Icons.signal_cellular_alt
                            : Icons.signal_cellular_alt_outlined,
                        size: 16,
                        color: Colors.orange,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Address
              Row(
                children: [
                  const Icon(Icons.location_on, size: 16, color: Colors.red),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(c['address'] ?? '',
                        style: const TextStyle(fontSize: 13, color: Colors.black54)),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              // SLA countdown
              if (slaDl != null && slaDl.isNotEmpty) ...[
                SLACountdown(slaDeadlineIso: slaDl),
                const SizedBox(height: 12),
              ],

              // Photos
              if (photos.isNotEmpty) ...[
                const Text('Photos',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                SizedBox(
                  height: 100,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: photos.length,
                    itemBuilder: (_, i) => Container(
                      width: 100,
                      margin: const EdgeInsets.only(right: 8),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(8),
                        color: Colors.grey[200],
                      ),
                      child: const Icon(Icons.image, size: 40, color: Colors.grey),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
              ],

              // Timeline
              if (timeline.isNotEmpty) ...[
                const Text('Timeline',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                EscalationTimeline(timeline: timeline),
                const SizedBox(height: 12),
              ],

              // Join/Member button
              if (_isMember)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.green[50],
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.green),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle, color: Colors.green),
                      SizedBox(width: 8),
                      Text('You are a member of this campaign',
                          style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold)),
                    ],
                  ),
                )
              else
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _isJoining ? null : _joinCampaign,
                    icon: _isJoining
                        ? const SizedBox(
                            height: 16,
                            width: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.group_add),
                    label: Text(_isJoining ? 'Joining...' : 'Join Campaign'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF1565C0),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
              const SizedBox(height: 24),
            ],
          ),
        );
      },
    );
  }

  Widget _statusBadge(String status) {
    final colors = {
      'open': Colors.grey,
      'acknowledged_pending': Colors.blue,
      'in_progress': Colors.orange,
      'resolved': Colors.green,
      'verifying': Colors.purple,
      'closed': Colors.green[700],
      'reopened': Colors.deepOrange,
    };
    return Chip(
      label: Text(status.replaceAll('_', ' ').toUpperCase(),
          style: const TextStyle(color: Colors.white, fontSize: 11)),
      backgroundColor: colors[status] ?? Colors.grey,
    );
  }
}
