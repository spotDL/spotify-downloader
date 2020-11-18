from multiprocess.pool import Pool

from typing import Callable, Any

class WorkerPool():
    def __init__(self, poolSize: int = 4):
        self.__workerPool = Pool(poolSize)

    def do(self, function:Callable, *args: Any) -> Any:
        maxArgLength = 0

        for arg in args:
            if isinstance(arg, list):
                if maxArgLength != 0 and len(arg) != maxArgLength:
                    raise Exception('variable imputs should be of the same length')

                elif maxArgLength == 0:
                    maxArgLength = len(arg)

        preparedArgs = []    

        for index in range(maxArgLength):
            cArg = []

            for arg in args:
                if isinstance(arg, list):
                    cArg.append(arg[index])
                else:
                    cArg.append(arg)

            preparedArgs.append(tuple(cArg))

        results = self.__workerPool.starmap(
            func = function,
            iterable = preparedArgs
        )

        return results
    
    def close(self):
        self.__workerPool.close()