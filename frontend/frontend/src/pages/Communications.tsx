import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Mail, Video, MapPin, Calendar, Clock, User } from 'lucide-react';

interface EmailItem {
  email_id: number;
  subject: string;
  body: string;
  sent_at: string;
  sender?: { first_name: string; last_name: string; email: string };
  receiver?: { first_name: string; last_name: string; email: string };
}

interface MeetingItem {
  meeting_id: number;
  meeting_title: string;
  meeting_date: string;
  meeting_room: string;
  minutes: string;
  organizer?: { first_name: string; last_name: string };
}

export const Communications: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'emails' | 'meetings'>('emails');
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [meetings, setMeetings] = useState<MeetingItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedEmail, setSelectedEmail] = useState<EmailItem | null>(null);
  const [selectedMeeting, setSelectedMeeting] = useState<MeetingItem | null>(null);

  useEffect(() => {
    const loadComms = async () => {
      setLoading(true);
      try {
        if (activeTab === 'emails') {
          const res = await api.communications.getEmails();
          setEmails(res || []);
          if (res && res.length > 0) {
            setSelectedEmail(res[0]);
          }
        } else {
          const res = await api.communications.getMeetings();
          setMeetings(res || []);
          if (res && res.length > 0) {
            setSelectedMeeting(res[0]);
          }
        }
      } catch (err) {
        console.error('Failed to load communications:', err);
      } finally {
        setLoading(false);
      }
    };
    loadComms();
  }, [activeTab]);

  return (
    <div className="animated-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px', height: '100%' }}>
      {/* Tab Controls */}
      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <button
          onClick={() => setActiveTab('emails')}
          className={`btn ${activeTab === 'emails' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
        >
          <Mail size={16} /> Work Emails Inbox
        </button>
        <button
          onClick={() => setActiveTab('meetings')}
          className={`btn ${activeTab === 'meetings' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
        >
          <Video size={16} /> Calendar & Meetings
        </button>
      </div>

      {loading ? (
        <div className="glass-card" style={{ padding: '40px', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Retrieving message logs...</p>
        </div>
      ) : activeTab === 'emails' ? (
        /* Emails Split View */
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          {/* Inbox List */}
          <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <h3>Inbox</h3>
            {emails.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>Inbox is empty.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '450px', overflowY: 'auto' }}>
                {emails.map(email => (
                  <div
                    key={email.email_id}
                    onClick={() => setSelectedEmail(email)}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      cursor: 'pointer',
                      backgroundColor: selectedEmail?.email_id === email.email_id ? 'rgba(99, 102, 241, 0.08)' : 'rgba(255, 255, 255, 0.01)',
                      borderColor: selectedEmail?.email_id === email.email_id ? 'var(--color-primary)' : 'var(--border-color)',
                      transition: 'var(--transition-fast)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      <span>From: {email.sender?.first_name || 'System'}</span>
                      <span>{email.sent_at ? new Date(email.sent_at).toLocaleDateString() : ''}</span>
                    </div>
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '4px' }}>{email.subject || '(No Subject)'}</h4>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {email.body}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Email Reading Pane */}
          <div className="glass-card">
            {selectedEmail ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div>
                  <h2 style={{ fontSize: '1.4rem', marginBottom: '8px' }}>{selectedEmail.subject || '(No Subject)'}</h2>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem', color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
                    <p><strong>From:</strong> {selectedEmail.sender ? `${selectedEmail.sender.first_name} ${selectedEmail.sender.last_name} (${selectedEmail.sender.email})` : 'System'}</p>
                    <p><strong>To:</strong> {selectedEmail.receiver ? `${selectedEmail.receiver.first_name} ${selectedEmail.receiver.last_name} (${selectedEmail.receiver.email})` : 'You'}</p>
                    <p style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      <Clock size={12} /> Sent: {selectedEmail.sent_at ? new Date(selectedEmail.sent_at).toLocaleString() : 'N/A'}
                    </p>
                  </div>
                </div>

                <div style={{
                  fontSize: '0.95rem',
                  lineHeight: 1.6,
                  color: 'var(--text-secondary)',
                  whiteSpace: 'pre-wrap',
                  backgroundColor: 'rgba(0,0,0,0.1)',
                  padding: '16px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)'
                }}>
                  {selectedEmail.body}
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>Select an email from the inbox list to read.</p>
            )}
          </div>
        </div>
      ) : (
        /* Meetings Split View */
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          {/* Calendar List */}
          <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <h3>Calendar Schedule</h3>
            {meetings.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No meetings scheduled.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '450px', overflowY: 'auto' }}>
                {meetings.map(meet => (
                  <div
                    key={meet.meeting_id}
                    onClick={() => setSelectedMeeting(meet)}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      cursor: 'pointer',
                      backgroundColor: selectedMeeting?.meeting_id === meet.meeting_id ? 'rgba(99, 102, 241, 0.08)' : 'rgba(255, 255, 255, 0.01)',
                      borderColor: selectedMeeting?.meeting_id === meet.meeting_id ? 'var(--color-primary)' : 'var(--border-color)',
                      transition: 'var(--transition-fast)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--color-primary)', fontWeight: 600, marginBottom: '6px' }}>
                      <Calendar size={12} /> {meet.meeting_date ? new Date(meet.meeting_date).toLocaleDateString() : 'N/A'}
                    </div>
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '4px' }}>{meet.meeting_title}</h4>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <MapPin size={12} /> Room: {meet.meeting_room || 'Online'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Meeting Minutes Reading Pane */}
          <div className="glass-card">
            {selectedMeeting ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div>
                  <h2 style={{ fontSize: '1.4rem', marginBottom: '8px' }}>{selectedMeeting.meeting_title}</h2>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem', color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
                    <p style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <User size={14} /> <strong>Organizer:</strong> {selectedMeeting.organizer ? `${selectedMeeting.organizer.first_name} ${selectedMeeting.organizer.last_name}` : 'Unassigned'}
                    </p>
                    <p style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <MapPin size={14} /> <strong>Location:</strong> {selectedMeeting.meeting_room || 'Online Video Conferencing'}
                    </p>
                    <p style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      <Clock size={14} /> Scheduled: {selectedMeeting.meeting_date ? new Date(selectedMeeting.meeting_date).toLocaleString() : 'N/A'}
                    </p>
                  </div>
                </div>

                <div>
                  <h3 style={{ fontSize: '1rem', marginBottom: '10px' }}>Meeting Minutes & Summary</h3>
                  <div style={{
                    fontSize: '0.95rem',
                    lineHeight: 1.6,
                    color: 'var(--text-secondary)',
                    whiteSpace: 'pre-wrap',
                    backgroundColor: 'rgba(0,0,0,0.1)',
                    padding: '16px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)'
                  }}>
                    {selectedMeeting.minutes || 'No minutes recorded for this session.'}
                  </div>
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>Select a meeting from the calendar list to view details.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
export default Communications;
