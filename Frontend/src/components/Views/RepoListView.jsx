import { Plus, Folder, RotateCw, Trash2 } from 'lucide-react';
import { motion } from 'motion/react';
import { useEffect, useState } from 'react';

import { deleteRepo, listRepos } from '../../api/repositories';

export default function RepoListView({ onIndexNew, onSelectRepo, onReindex, refreshKey = 0 }) {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadRepos = async () => {
      try {
        setLoading(true);
        setError('');
        const rows = await listRepos();
        if (isMounted) {
          setRepos(rows);
        }
      } catch (loadError) {
        if (isMounted) {
          setError(
            loadError.response?.data?.detail ||
            loadError.message ||
            'Failed to load repositories'
          );
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadRepos();

    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  const handleDelete = async (event, repoId) => {
    event.stopPropagation();

    try {
      await deleteRepo(repoId);
      setRepos((current) => current.filter((repo) => repo.id !== repoId));
    } catch (deleteError) {
      setError(
        deleteError.response?.data?.detail ||
        deleteError.message ||
        'Failed to delete repository'
      );
    }
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto min-h-screen">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-end mb-10">
          <div>
            <h1 className="text-3xl font-bold text-on-surface mb-2">Repositories</h1>
            <p className="text-on-surface-variant">Manage connected source code repositories and indexing status.</p>
          </div>
          <button
            onClick={onIndexNew}
            className="bg-primary text-on-primary px-5 py-2.5 rounded-lg font-bold text-xs uppercase tracking-widest flex items-center gap-2 hover:bg-primary/90 transition-all shadow-sm cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Connect New Repository
          </button>
        </div>

        {error ? (
          <p className="text-sm text-red-400 mb-6">{error}</p>
        ) : null}

        <div className="bg-surface-container rounded-2xl border border-outline-variant overflow-hidden shadow-2xl shadow-black/20">
          <div className="grid grid-cols-12 gap-4 px-6 py-4 bg-surface-container-highest/50 border-b border-outline-variant text-[10px] font-bold text-on-surface-variant uppercase tracking-[0.1em]">
            <div className="col-span-12 md:col-span-4">Repository Name</div>
            <div className="hidden md:block col-span-2">Status</div>
            <div className="hidden md:block col-span-2">Languages</div>
            <div className="hidden md:block col-span-3">Path</div>
            <div className="hidden md:block col-span-1">Actions</div>
          </div>

          <div className="flex flex-col min-h-[200px] justify-center items-center">
            {loading ? (
              <div className="flex flex-col items-center gap-4 text-outline py-12">
                <p className="text-sm font-medium uppercase tracking-widest">Loading repositories...</p>
              </div>
            ) : repos.length > 0 ? (
              repos.map((repo, index) => (
                <motion.div
                  key={repo.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => onSelectRepo(repo)}
                  className="grid grid-cols-12 gap-4 px-6 py-5 items-center border-b border-outline-variant/30 hover:bg-surface-container-highest/30 transition-colors group cursor-pointer w-full"
                >
                  <div className="col-span-12 md:col-span-4 flex items-center gap-4">
                    <div className="p-2 rounded bg-surface-container-highest border border-outline-variant/50">
                      <Folder className="w-4 h-4 text-outline" />
                    </div>
                    <span className="font-mono text-sm text-primary font-medium">{repo.name}</span>
                  </div>

                  <div className="col-span-6 md:col-span-2 flex items-center">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider ${
                      repo.languages?.length
                        ? 'border-secondary/30 text-secondary bg-secondary/5'
                        : 'border-tertiary/30 text-tertiary bg-tertiary/5'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${repo.languages?.length ? 'bg-secondary' : 'bg-tertiary animate-pulse'}`}></span>
                      {repo.languages?.length ? 'ready' : 'uploaded'}
                    </span>
                  </div>

                  <div className="hidden md:block col-span-2 font-mono text-sm text-on-surface-variant">
                    {repo.languages?.join(', ') || '-'}
                  </div>

                  <div className="hidden md:block col-span-3 text-sm text-on-surface-variant truncate">
                    {repo.path}
                  </div>

                  <div className="col-span-6 md:col-span-1 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        onReindex(repo);
                      }}
                      className="p-2 rounded-lg text-outline-variant hover:text-primary hover:bg-primary/10 transition-colors"
                    >
                      <RotateCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(event) => handleDelete(event, repo.id)}
                      className="p-2 rounded-lg text-outline-variant hover:text-error hover:bg-error/10 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="flex flex-col items-center gap-4 text-outline py-12">
                <Folder className="w-12 h-12 opacity-20" />
                <p className="text-sm font-medium uppercase tracking-widest">No repositories indexed yet</p>
                <button
                  onClick={onIndexNew}
                  className="text-primary text-[10px] font-black underline uppercase tracking-tighter hover:text-primary/80 transition-colors cursor-pointer"
                >
                  Start New Analysis
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
