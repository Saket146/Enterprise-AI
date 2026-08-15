import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { ListTodo, Milestone as MilestoneIcon, Calendar, User, DollarSign, ArrowRight } from 'lucide-react';

interface ProjectItem {
  project_id: number;
  project_name: string;
  project_code: string;
  status: string;
  start_date: string;
  end_date: string;
  budget: number;
  priority: string;
  description: string;
  manager?: { first_name: string; last_name: string };
  department?: { department_name: string };
}

interface TaskItem {
  task_id: number;
  title: string;
  status: string;
  priority: string;
  due_date: string;
  assignee?: { first_name: string; last_name: string };
}

interface MilestoneItem {
  milestone_id: number;
  milestone_name: string;
  due_date: string;
  status: string;
}

export const Projects: React.FC = () => {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [milestones, setMilestones] = useState<MilestoneItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [detailsLoading, setDetailsLoading] = useState<boolean>(false);
  const [search, setSearch] = useState<string>('');

  // Load all projects
  useEffect(() => {
    const loadProjects = async () => {
      setLoading(true);
      try {
        const res = await api.projects.list({ search });
        setProjects(res || []);
        if (res && res.length > 0 && !selectedProjectId) {
          setSelectedProjectId(res[0].project_id);
        }
      } catch (err) {
        console.error('Failed to load projects:', err);
      } finally {
        setLoading(false);
      }
    };
    loadProjects();
  }, [search]);

  // Load selected project's tasks and milestones
  useEffect(() => {
    if (!selectedProjectId) return;

    const loadProjectDetails = async () => {
      setDetailsLoading(true);
      try {
        const tasksRes = await api.projects.getTasks(selectedProjectId);
        setTasks(tasksRes || []);

        const milestonesRes = await api.projects.getMilestones(selectedProjectId);
        setMilestones(milestonesRes || []);
      } catch (err) {
        console.error('Failed to load project details:', err);
      } finally {
        setDetailsLoading(false);
      }
    };
    loadProjectDetails();
  }, [selectedProjectId]);

  const selectedProject = projects.find(p => p.project_id === selectedProjectId);

  // Compute tasks progress percentages
  const completedTasks = tasks.filter(t => t.status === 'Completed' || t.status === 'completed').length;
  const progressPercent = tasks.length > 0 ? Math.round((completedTasks / tasks.length) * 100) : 0;

  return (
    <div className="animated-fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px', height: '100%' }}>
      {/* 1. Projects Sidebar Search & List */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '20px', height: 'fit-content' }}>
        <h3>Projects Boards</h3>
        <input
          className="input-field"
          type="text"
          placeholder="Filter projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {loading ? (
          <p style={{ color: 'var(--text-secondary)' }}>Loading boards...</p>
        ) : projects.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)' }}>No projects found.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {projects.map(proj => (
              <div
                key={proj.project_id}
                onClick={() => setSelectedProjectId(proj.project_id)}
                style={{
                  padding: '16px',
                  borderRadius: '12px',
                  border: '1px solid var(--border-color)',
                  cursor: 'pointer',
                  backgroundColor: selectedProjectId === proj.project_id ? 'rgba(99, 102, 241, 0.08)' : 'rgba(255, 255, 255, 0.01)',
                  borderColor: selectedProjectId === proj.project_id ? 'var(--color-primary)' : 'var(--border-color)',
                  transition: 'var(--transition-fast)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary)' }}>{proj.project_code}</span>
                  <span className={`badge ${proj.status === 'Active' ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.65rem' }}>
                    {proj.status}
                  </span>
                </div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '4px' }}>{proj.project_name}</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Dept: {proj.department?.department_name || 'No Dept'}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. Project Details pane */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {selectedProject ? (
          <>
            {/* Project Overview Card */}
            <div className="glass-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-primary)', fontWeight: 700 }}>{selectedProject.project_code}</span>
                  <h2 style={{ fontSize: '1.6rem', marginTop: '4px' }}>{selectedProject.project_name}</h2>
                </div>
                <span className={`badge ${selectedProject.priority === 'High' ? 'badge-danger' : 'badge-success'}`}>
                  {selectedProject.priority} Priority
                </span>
              </div>

              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '24px', lineHeight: 1.5 }}>
                {selectedProject.description || 'No project description supplied.'}
              </p>

              {/* Project Meta Metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '16px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <User size={18} style={{ color: 'var(--text-secondary)' }} />
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PROJECT MANAGER</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 500 }}>
                      {selectedProject.manager ? `${selectedProject.manager.first_name} ${selectedProject.manager.last_name}` : 'Unassigned'}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Calendar size={18} style={{ color: 'var(--text-secondary)' }} />
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>DELIVERY DATE</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 500 }}>{selectedProject.end_date || 'Ongoing'}</div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <DollarSign size={18} style={{ color: 'var(--text-secondary)' }} />
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PROJECT BUDGET</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 500 }}>
                      {selectedProject.budget ? `$${Number(selectedProject.budget).toLocaleString()}` : '$0.00'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Task Tracking Card */}
            <div className="glass-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ListTodo size={18} /> Action Items & Tasks
                </h3>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {completedTasks} / {tasks.length} Tasks Completed
                </span>
              </div>

              {/* Progress Bar */}
              <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden', marginBottom: '24px' }}>
                <div style={{ width: `${progressPercent}%`, height: '100%', background: 'var(--accent-gradient)', borderRadius: '4px', transition: 'width 0.4s ease' }} />
              </div>

              {detailsLoading ? (
                <p style={{ color: 'var(--text-secondary)' }}>Loading task nodes...</p>
              ) : tasks.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)' }}>No tasks assigned to this board.</p>
              ) : (
                <div className="table-container">
                  <table className="enterprise-table">
                    <thead>
                      <tr>
                        <th>Task Details</th>
                        <th>Assignee</th>
                        <th>Status</th>
                        <th>Priority</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tasks.map(task => (
                        <tr key={task.task_id}>
                          <td style={{ fontSize: '0.9rem', fontWeight: 500 }}>{task.title}</td>
                          <td style={{ fontSize: '0.85rem' }}>
                            {task.assignee ? `${task.assignee.first_name} ${task.assignee.last_name}` : 'Unassigned'}
                          </td>
                          <td>
                            <span className={`badge ${task.status === 'Completed' || task.status === 'completed' ? 'badge-success' : 'badge-warning'}`}>
                              {task.status}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.85rem', fontWeight: 600 }}>{task.priority}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Milestones Card */}
            <div className="glass-card">
              <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <MilestoneIcon size={18} /> Project Milestones
              </h3>

              {detailsLoading ? (
                <p style={{ color: 'var(--text-secondary)' }}>Loading milestones...</p>
              ) : milestones.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)' }}>No milestones registered for this project.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {milestones.map(ms => (
                    <div
                      key={ms.milestone_id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '16px',
                        borderRadius: '12px',
                        border: '1px solid var(--border-color)',
                        backgroundColor: 'rgba(255, 255, 255, 0.01)'
                      }}
                    >
                      <div>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{ms.milestone_name}</h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                          <Calendar size={12} /> Target date: {ms.due_date || 'N/A'}
                        </div>
                      </div>
                      <span className={`badge ${ms.status === 'Completed' ? 'badge-success' : 'badge-warning'}`}>
                        {ms.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="glass-card" style={{ padding: '40px', textAlign: 'center' }}>
            <p style={{ color: 'var(--text-secondary)' }}>Select a project board from the sidebar to inspect items.</p>
          </div>
        )}
      </div>
    </div>
  );
};
export default Projects;
