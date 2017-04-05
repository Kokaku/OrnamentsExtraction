import os
import keras.backend.tensorflow_backend as KTF
import tensorflow as tf

def configureGpu(gpuId='0', mode='limit', limit=0.2):
    """
    Configure GPU usage for Keras with Tensorflow.

    Parameters
    ----------
    gpuId: string
        A string containing all used GPU. GPU ids are comma separated.
        By example: '0' or '0,1'
    mode: string
        Mode can takes two value: 'limit' or 'growth'. With 'limit', a predifined size
        of GPU memory is allocated. With 'growth', tensorflow will automatically allocat
        what it need. However, it doesn't unallocate.
    limit: float
        If in mode 'limit', the fraction of total GPU memory to allocate
    """

    os.environ["CUDA_VISIBLE_DEVICES"] = gpuId
    tf.python.control_flow_ops = tf
    if mode == 'growth':
        KTF.set_session(getsessionWithMemoryGrowth())
    else:
        KTF.set_session(getSessionWithMemoryLimit(limit))

def getSessionWithMemoryLimit(gpu_fraction=0.3):
    num_threads = os.environ.get('OMP_NUM_THREADS')
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=gpu_fraction)

    if num_threads:
        return tf.Session(config=tf.ConfigProto(
            gpu_options=gpu_options, intra_op_parallelism_threads=num_threads))
    else:
        return tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))

def getsessionWithMemoryGrowth():
    num_threads = os.environ.get('OMP_NUM_THREADS')
    gpu_options = tf.GPUOptions(allow_growth = True)

    if num_threads:
        return tf.Session(config=tf.ConfigProto(
            gpu_options=gpu_options, intra_op_parallelism_threads=num_threads))
    else:
        return tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))