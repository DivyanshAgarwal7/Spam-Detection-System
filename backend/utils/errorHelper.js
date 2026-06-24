// utils/errorHelper.js

const errorCodes={
    //Auth errors
    UNAUTHORIZED: 'UNAUTHORIZED',
    FORBIDDEN: 'FORBIDDEN',
    INVALID_TOKEN: 'INVALID_TOKEN',

    //Input errors
    INVALID_INPUT: 'INVALID_INPUT',
    MISSING_FIELD: 'MISSING_FIELD',
    VALIDATION_ERROR: 'VALIDATION_ERROR',

    //Resource errors
    NOT_FOUND: 'NOT_FOUND',
    ALREADY_EXISTS: 'ALREADY_EXISTS',

    //Server errors
    INTERNAL_SERVER_ERROR: 'INTERNAL_SERVER_ERROR',
    SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',

    //Payload errors
    PAYLOAD_TOO_LARGE: 'PAYLOAD_TOO_LARGE',
};

//Standard error formattter
const formatError = (code, message, details = null) => {
    const error={
        code,
        message,
    };
    if(details){
        error.details=details;
    }   return error;
};

//Express middleware for handling errors
const errorHandler = (err, req, res, next) => {
    //Handle specific error types
    if (err.name === 'ValidationError') {
        return res.status(400).json(formatError(
            errorCodes.VALIDATION_ERROR,
            err.message,
            err.errors
        ));
    }
    
    if (err.name === 'CastError') {
        return res.status(400).json(formatError(
            errorCodes.INVALID_INPUT,
            'Invalid ID format'
        ));
    }
    
    if (err.code === 11000) {
        return res.status(409).json(formatError(
            errorCodes.ALREADY_EXISTS,
            'Duplicate key error'
        ));
    }
    
    // Default error
    const status = err.status || 500;
    const code = err.code || errorCodes.INTERNAL_SERVER_ERROR;
    const message = err.message || 'Internal server error';
    
    res.status(status).json(formatError(code, message));
};

module.exports = {
    formatError,
    errorHandler,
    errorCodes
};