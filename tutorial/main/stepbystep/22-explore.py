from tutorial.main.stepbystep.stepbysteputils.pgconnector import create_engine_ready
import pandas as pd
from suricate.explore import Explorer
from suricate.base import multiindex21column

engine = create_engine_ready()

n_questions = 100

# nrows = 50
# Xst = pd.read_sql(sql="SELECT * FROM es_scores LIMIT {}".format(nrows), con=engine).set_index(['ix_source', 'ix_target'], drop=True)[['ix', 'es_score']]
# Xsbs = pd.read_sql(sql="SELECT * FROM es_sbs LIMIT {}".format(nrows), con=engine).set_index(['ix_source', 'ix_target'], drop=True)
Xst = pd.read_sql(sql="SELECT * FROM es_scores", con=engine).set_index(['ix_source', 'ix_target'], drop=True)[['ix', 'es_score']]
Xsbs = pd.read_sql(sql="SELECT * FROM es_sbs", con=engine).set_index(['ix_source', 'ix_target'], drop=True)


# REBUILD Y_true
y_true = pd.read_sql(sql="SELECT * FROM y_true WHERE y_true.y_true = 1", con=engine).set_index(['ix_source', 'ix_target'], drop=True)
y_truetemp=Xst[['ix']]
y_truetemp['y_true']=0
y_truetemp.loc[y_true.index.intersection(Xst.index), 'y_true'] = y_true.loc[y_true.index.intersection(Xst.index), 'y_true']
y_true = y_truetemp.copy()
del y_truetemp
### y_true has now a multiindex, ix, and y_true columns


## Fit the cluster to non-supervized data
exp = Explorer(n_simple=n_questions, n_hard=n_questions)
exp.fit_cluster(X=Xst[['es_score']])
y_cluster = pd.Series(data=exp.pred_cluster(X=Xst), index=Xst.index, name='y_cluster')
X_cluster = pd.DataFrame(y_cluster)
X_cluster['avg_score'] = Xst[['es_score']].mean(axis=1)
X_cluster['y_true'] = y_true['y_true']
X_cluster['ix']=Xst['ix']
X_cluster.reset_index(inplace=True, drop=False)
X_cluster.set_index('ix', inplace=True)
X_cluster = X_cluster[[ 'ix_source', 'ix_target', 'avg_score', 'y_cluster','y_true']]
X_cluster.to_sql('cluster_output', con=engine, if_exists='replace')

### Ask simple questions
ix_simple = exp.ask_simple(X=Xst)
Sbs_simple = Xsbs.loc[ix_simple]
y_simple = y_true.loc[ix_simple]['y_true']

### Fit the cluser with supervized data
exp.fit(X=Xst, y=y_simple, fit_cluster=False)

### Ask hard (pointed) questions
ix_hard = exp.ask_hard(X=Xst, y=y_simple)
Sbs_hard = Xsbs.loc[ix_hard]
y_hard = y_true.loc[ix_hard]['y_true']

### Obtain the results of the labels
y_questions = y_true.loc[ix_hard.union(ix_simple)]['y_true']
X_questions = Xsbs.loc[y_questions.index].copy()
X_questions['y_cluster'] = y_cluster
X_questions['y_true'] = y_questions
X_questions.reset_index(inplace=True, drop=False)
X_questions.set_index('ix', inplace=True)
# REORDER COLS
X_questions = X_questions[[c for c in Xsbs.columns if c!= 'ix' ] + ['y_cluster', 'y_true']]
X_questions.to_sql('questions', con=engine, if_exists='replace')



