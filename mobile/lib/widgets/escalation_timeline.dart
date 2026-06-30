import 'package:flutter/material.dart';

/// WardWatch - Escalation Timeline Widget (Step 5.3)
///
/// Takes timeline array (List<Map<String,dynamic>>) as input.
/// Vertical timeline with colored dots and icons per stage.
/// Current stage (last item) is highlighted.
/// Shows timestamp and actor for each event.
///
/// Stage colors:
///   created, threshold_met, routing_drafted, citizen_joined → blue
///   status_updated, in_progress → amber
///   escalated, verification_failed → red
///   verified_and_closed, closed → green
///   mass_issue_flagged, reopened → orange
///   verifying → purple
///   request_more_info → teal
class EscalationTimeline extends StatelessWidget {
  final List<Map<String, dynamic>> timeline;

  const EscalationTimeline({
    super.key,
    required this.timeline,
  });

  @override
  Widget build(BuildContext context) {
    if (timeline.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text('No timeline events.', style: TextStyle(color: Colors.white38)),
      );
    }

    return Column(
      children: List.generate(timeline.length, (index) {
        final event = timeline[index];
        final isLast = index == timeline.length - 1;
        return _TimelineItem(
          event: event,
          isLast: isLast,
          isCurrent: isLast,
        );
      }),
    );
  }
}

class _TimelineItem extends StatelessWidget {
  final Map<String, dynamic> event;
  final bool isLast;
  final bool isCurrent;

  const _TimelineItem({
    required this.event,
    required this.isLast,
    required this.isCurrent,
  });

  Color get _dotColor {
    final action = event['action'] as String? ?? '';
    switch (action) {
      case 'created':
      case 'threshold_met':
      case 'routing_drafted':
      case 'citizen_joined':
        return Colors.blue;
      case 'status_updated':
      case 'in_progress':
      case 'acknowledged':
        return Colors.amber;
      case 'escalated':
      case 'verification_failed':
        return Colors.red;
      case 'verified_and_closed':
      case 'closed':
        return Colors.green;
      case 'mass_issue_flagged':
      case 'reopened':
        return Colors.orange;
      case 'verifying':
        return Colors.purple;
      case 'request_more_info':
        return Colors.teal;
      default:
        return Colors.grey;
    }
  }

  IconData get _icon {
    final action = event['action'] as String? ?? '';
    switch (action) {
      case 'created': return Icons.add_circle_outline;
      case 'citizen_joined': return Icons.person_add;
      case 'threshold_met': return Icons.groups;
      case 'routing_drafted': return Icons.send_outlined;
      case 'status_updated': return Icons.update;
      case 'acknowledged': return Icons.check_circle_outline;
      case 'in_progress': return Icons.construction;
      case 'escalated': return Icons.arrow_upward;
      case 'verification_failed': return Icons.cancel;
      case 'verified_and_closed': return Icons.verified;
      case 'closed': return Icons.lock;
      case 'mass_issue_flagged': return Icons.report;
      case 'reopened': return Icons.refresh;
      case 'verifying': return Icons.how_to_vote;
      case 'request_more_info': return Icons.help_outline;
      default: return Icons.circle;
    }
  }

  String get _actionLabel {
    final action = event['action'] as String? ?? '';
    const labels = <String, String>{
      'created': 'Campaign Created',
      'citizen_joined': 'Citizen Joined',
      'threshold_met': 'Threshold Met (3+ Citizens)',
      'routing_drafted': 'Routing Draft Created',
      'status_updated': 'Status Updated',
      'acknowledged': 'Acknowledged by Official',
      'in_progress': 'Marked In Progress',
      'escalated': 'Escalated to Higher Level',
      'verification_failed': 'Verification Failed — Reopened',
      'verified_and_closed': 'Verified & Closed',
      'closed': 'Campaign Closed',
      'mass_issue_flagged': 'Flagged as Mass Issue',
      'reopened': 'Campaign Reopened',
      'verifying': 'Verification Window Started',
      'request_more_info': 'More Information Requested',
    };
    return labels[action] ?? action.replaceAll('_', ' ').toUpperCase();
  }

  String _formatActor(String actor) {
    if (actor == 'system') return '🤖 System';
    if (actor.length > 12) return '👤 ${actor.substring(0, 8)}...';
    return '👤 $actor';
  }

  String _formatTimestamp(String? ts) {
    if (ts == null || ts.isEmpty) return '';
    try {
      final dt = DateTime.parse(ts).toLocal();
      return '${dt.day}/${dt.month}/${dt.year} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return ts;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _dotColor;
    final actor = event['actor'] as String? ?? '';
    final notes = event['notes'] as String? ?? '';
    final timestamp = event['timestamp'] as String? ?? '';

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline line + dot
          SizedBox(
            width: 32,
            child: Column(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: isCurrent ? color : color.withOpacity(0.3),
                    shape: BoxShape.circle,
                    border: isCurrent
                        ? Border.all(color: color, width: 2)
                        : null,
                    boxShadow: isCurrent
                        ? [BoxShadow(color: color.withOpacity(0.4), blurRadius: 8, spreadRadius: 2)]
                        : null,
                  ),
                  child: Icon(_icon, color: Colors.white, size: 14),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: Colors.white.withOpacity(0.1),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          // Content
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 20),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: isCurrent
                    ? BoxDecoration(
                        color: color.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: color.withOpacity(0.3)),
                      )
                    : null,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            _actionLabel,
                            style: TextStyle(
                              color: isCurrent ? color : Colors.white,
                              fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500,
                              fontSize: 13,
                            ),
                          ),
                        ),
                        if (isCurrent)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: color.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              'CURRENT',
                              style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                            ),
                          ),
                      ],
                    ),
                    if (notes.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        notes,
                        style: const TextStyle(color: Colors.white54, fontSize: 11),
                      ),
                    ],
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Text(
                          _formatActor(actor),
                          style: TextStyle(color: color.withOpacity(0.7), fontSize: 11),
                        ),
                        const Spacer(),
                        Text(
                          _formatTimestamp(timestamp),
                          style: const TextStyle(color: Colors.white38, fontSize: 10),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
